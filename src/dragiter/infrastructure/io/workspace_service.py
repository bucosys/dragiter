# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Run workspace, shard persist, Assembly and commit.

Implements ``dragiter_ap_staging_v2.md`` (v2.1). Section numbers in comments
refer to that profile.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import enum
import logging
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import TextIO

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import OutputParameters
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.ports.output_commit_service import OutputCommitError
from dragiter.domain.ports.persistence_service import (
    PersistenceConflictError,
    PersistenceError,
)
from dragiter.infrastructure.io.filename_utils import (
    ensure_path_within_directory,
    format_output_filename,
    format_timestamp_ns,
    schema_has_runtime_tokens,
)
from dragiter.infrastructure.io.io_services import write_or_append_lines_to_unique_file

logger = logging.getLogger(__name__)

# Section 5.2: one prefix per sink, never a shared workspace.
DIR_STAGING_PREFIX = ".tmp_staging_dir_"
FILE_STAGING_PREFIX = ".tmp_staging_file_"
STDOUT_STAGING_PREFIX = ".tmp_staging_stdout_"

# Section 6.1: res<N>, zero-padded, fixed width, no automatic widening.
SHARD_PREFIX = "res"
SHARD_DIGITS = 6
SHARD_LIMIT = 10**SHARD_DIGITS - 1
_SHARD_RE = re.compile(rf"^{SHARD_PREFIX}\d{{{SHARD_DIGITS}}}$")

# Section 7.9: Assembly result for stdout-only.
STDOUT_CONTENT_NAME = "stdout.txt"

EXCLUSIVE_RUNTIME_NOTICE = (
    "output_mode x: early name check skipped because output_filename_schema "
    "contains TIMESTAMP; exclusive create is enforced at commit."
)


class WorkspaceError(PersistenceError):
    """Location, creation or persist failure of the run workspace."""


class WorkspaceConflictError(PersistenceConflictError):
    """Raised by the early check (Section 8), before any completion call."""


class WorkspaceCommitError(OutputCommitError):
    """Raised on preflight or transfer failure (Section 7). The workspace stays."""


class SinkKind(enum.Enum):
    DIRECTORY = "-O"
    FILE = "-o"
    STDOUT = "stdout"


@dataclass(frozen=True)
class WorkspaceLocation:
    """Where this run's workspace lives and what it commits to."""

    sink: SinkKind
    parent: Path
    path: Path
    # DIR for -O, FILE for -o. Unused for stdout-only.
    target: Path


def user_temp_directory(environ: Mapping[str, str]) -> Path:
    """
    Resolve the user's default temp directory (Section 3, "User temp").

    A set ``$TMPDIR`` is taken as given, even if unusable: the stdout sink then
    aborts before the first completion (criterion 33, step P4) instead of
    silently falling back elsewhere. Without ``$TMPDIR`` the platform default
    applies.
    """
    tmpdir = environ.get("TMPDIR", "")
    if tmpdir:
        return Path(tmpdir)
    return Path(tempfile.gettempdir())


class WorkspaceLayout:
    """Maps the output parameters of a run to its one workspace (Section 5)."""

    def __init__(self, pid: int, user_temp: Path) -> None:
        self._pid = pid
        self._user_temp = user_temp

    def locate(self, op: OutputParameters) -> WorkspaceLocation:
        file_set = op.output_file_path_setting.is_set
        dir_set = op.output_directory_path_setting.is_set
        if file_set and dir_set:
            # Section 1: mutually exclusive. The validator rejects this first;
            # repeated here so no workspace can ever be derived from it.
            raise WorkspaceError("-o and -O are mutually exclusive; use only one of them.")
        if dir_set:
            directory = Path(op.output_directory_path_setting.value)
            return WorkspaceLocation(
                SinkKind.DIRECTORY,
                directory,
                directory / f"{DIR_STAGING_PREFIX}{self._pid}",
                directory,
            )
        if file_set:
            file = Path(op.output_file_path_setting.value)
            return WorkspaceLocation(
                SinkKind.FILE,
                file.parent,
                file.parent / f"{FILE_STAGING_PREFIX}{self._pid}",
                file,
            )
        return WorkspaceLocation(
            SinkKind.STDOUT,
            self._user_temp,
            self._user_temp / f"{STDOUT_STAGING_PREFIX}{self._pid}",
            self._user_temp,
        )

    @staticmethod
    def check_parent(location: WorkspaceLocation) -> None:
        """Section 5.1: the parent must exist, be a directory and be writable."""
        parent = location.parent
        role = "user temp" if location.sink is SinkKind.STDOUT else f"{location.sink.value} parent"
        if not parent.is_dir():
            raise WorkspaceError(f"{role} is missing or not a directory: {parent}")
        if not os.access(parent, os.W_OK | os.X_OK):
            raise WorkspaceError(f"{role} is not writable: {parent}")


def shard_name(number: int) -> str:
    if number < 1 or number > SHARD_LIMIT:
        raise WorkspaceError(
            f"shard number {number} outside 1..{SHARD_LIMIT}; "
            f"at most {SHARD_LIMIT} completions per run and sink."
        )
    return f"{SHARD_PREFIX}{number:0{SHARD_DIGITS}d}"


def list_shards(workspace: Path) -> list[Path]:
    """All shards of *workspace* in ascending sequence order."""
    return sorted(p for p in workspace.iterdir() if p.is_file() and _SHARD_RE.match(p.name))


def _write_new_file(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _planned_directory_names(
    sessions: list[ChatSession], schema: str
) -> list[str]:
    return [
        format_output_filename(
            session.chunk, session.loop_item, index, schema, timestamp=None
        )
        for index, session in enumerate(sessions, start=1)
    ]


# --------------------------------------------------------------------------- #
# Persist (Section 6)
# --------------------------------------------------------------------------- #


class WorkspaceRun:
    """One run's workspace: every completion becomes one finished shard."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._count = 0

    @property
    def path(self) -> Path:
        return self._path

    def persist(self, index: int, session: ChatSession, result: ChatResult) -> None:
        # Sink-agnostic by design (Section 6): no delimiter, no filtering,
        # no final name. The shard number is workspace-local, not *index*.
        number = self._count + 1
        shard = self._path / shard_name(number)
        content = result.output_chat_message.content or ""
        try:
            _write_new_file(shard, content.encode("utf-8"))
        except OSError as exc:
            raise WorkspaceError(
                f"could not persist session {index} as {shard}: {exc}"
            ) from exc
        self._count = number


class WorkspacePersistenceService:
    """PersistenceService backed by one hidden workspace per run and sink."""

    def __init__(self, layout: WorkspaceLayout) -> None:
        self._layout = layout

    def open(
        self,
        op: OutputParameters,
        prompt_template: PromptTemplate,
        sessions: list[ChatSession],
    ) -> WorkspaceRun:
        location = self._layout.locate(op)
        self._layout.check_parent(location)
        self._early_check(
            location,
            op.output_mode_string_setting.value,
            prompt_template.output_filename_schema or "",
            sessions,
        )
        try:
            location.path.mkdir()
        except FileExistsError as exc:
            raise WorkspaceError(
                f"workspace already exists, refusing to mix runs: {location.path}"
            ) from exc
        except OSError as exc:
            raise WorkspaceError(f"could not create workspace {location.path}: {exc}") from exc
        return WorkspaceRun(location.path)

    @staticmethod
    def _early_check(
        location: WorkspaceLocation,
        mode: str,
        schema: str,
        sessions: list[ChatSession],
    ) -> None:
        """Section 8. Runs before the workspace exists."""
        conflicts: list[Path] = []

        if location.sink is SinkKind.FILE:
            if mode == "x" and location.target.exists():
                conflicts.append(location.target)

        elif location.sink is SinkKind.DIRECTORY:
            if schema_has_runtime_tokens(schema):
                print(EXCLUSIVE_RUNTIME_NOTICE, file=sys.stderr)
            else:
                seen: set[str] = set()
                for name in _planned_directory_names(sessions, schema):
                    planned = location.target / name
                    duplicate = name in seen
                    if duplicate or (mode == "x" and planned.exists()):
                        conflicts.append(planned)
                    seen.add(name)

        if conflicts:
            shown = ", ".join(str(path) for path in conflicts)
            raise WorkspaceConflictError(
                f"output_mode {mode}: refusing to start; target already exists "
                f"or is planned twice: {shown}"
            )


# --------------------------------------------------------------------------- #
# Assembly and commit (Section 7)
# --------------------------------------------------------------------------- #


def assemble(workspace: Path, content_name: str, delimiter: str) -> Path | None:
    """
    Section 7.0: merge all non-empty shards into *content_name* inside *workspace*.

    Returns None (and creates nothing) when every shard is empty (0 bytes).
    Shards stay in place.
    """
    if _SHARD_RE.match(content_name):
        raise WorkspaceCommitError(
            f"target name {content_name!r} collides with the shard naming scheme; "
            f"workspace: {workspace}"
        )
    blocks = [data for data in (shard.read_bytes() for shard in list_shards(workspace)) if data]
    if not blocks:
        return None
    assembled = workspace / content_name
    _write_new_file(assembled, delimiter.encode("utf-8").join(blocks))
    return assembled


def _append_block(source: Path, target: Path, delimiter: str) -> None:
    """Section 7.3: -m a."""
    block = source.read_bytes()
    if not block.decode("utf-8").strip():
        return
    if target.exists() and target.stat().st_size > 0:
        block = delimiter.encode("utf-8") + block
    with target.open("ab") as handle:
        handle.write(block)
        handle.flush()
        os.fsync(handle.fileno())


class WorkspaceCommitService:
    """OutputCommitService: transfers a run's workspace to its sink."""

    def __init__(self, layout: WorkspaceLayout, stdout: TextIO) -> None:
        self._layout = layout
        self._stdout = stdout

    def commit(
        self,
        op: OutputParameters,
        prompt_template: PromptTemplate,
        sessions: list[ChatSession],
    ) -> None:
        location = self._layout.locate(op)
        workspace = location.path
        if not workspace.is_dir():
            raise WorkspaceCommitError(f"workspace missing, nothing to commit: {workspace}")

        mode = op.output_mode_string_setting.value
        delimiter = prompt_template.output_delimiter or ""

        match location.sink:
            case SinkKind.DIRECTORY:
                self._commit_directory(
                    location,
                    mode,
                    delimiter,
                    prompt_template.output_filename_schema or "",
                    sessions,
                )
            case SinkKind.FILE:
                self._commit_file(location, mode, delimiter)
            case SinkKind.STDOUT:
                self._commit_stdout(location, delimiter)

        # Sections 7.4 / 7.9: only this run's own workspace, only on success.
        self._remove(workspace)

    def discard(self, op: OutputParameters) -> None:
        self._remove(self._layout.locate(op).path)

    # -- -O ---------------------------------------------------------------- #

    def _commit_directory(
        self,
        location: WorkspaceLocation,
        mode: str,
        delimiter: str,
        schema: str,
        sessions: list[ChatSession],
    ) -> None:
        workspace = location.path
        directory = location.target
        shards = list_shards(workspace)
        if len(shards) != len(sessions):
            raise WorkspaceCommitError(
                f"{len(shards)} shards for {len(sessions)} sessions; "
                f"target: {directory}; workspace: {workspace}"
            )

        moves: list[tuple[Path, Path]] = []
        for index, (shard, session) in enumerate(zip(shards, sessions, strict=True), start=1):
            # Section 6.3 / 7.5: {TIMESTAMP} is the shard's mtime, not the commit clock.
            timestamp = format_timestamp_ns(shard.stat().st_mtime_ns)
            name = format_output_filename(
                session.chunk, session.loop_item, index, schema, timestamp=timestamp
            )
            moves.append((shard, ensure_path_within_directory(directory / name, directory)))

        targets = [target for _, target in moves]
        duplicates = sorted({str(t) for t in targets if targets.count(t) > 1})
        if duplicates:
            raise WorkspaceCommitError(
                f"final names planned twice: {', '.join(duplicates)}; workspace: {workspace}"
            )
        if mode == "x":
            self._preflight_exclusive(targets, workspace)

        for shard, target in moves:
            self._transfer(shard, target, mode, delimiter, workspace)

    # -- -o ---------------------------------------------------------------- #

    def _commit_file(self, location: WorkspaceLocation, mode: str, delimiter: str) -> None:
        workspace = location.path
        target = location.target
        assembled = self._assemble(workspace, target.name, delimiter, str(target))
        if assembled is None:
            return  # Section 7.8: FILE is neither created nor modified.
        if mode == "x":
            self._preflight_exclusive([target], workspace)
        self._transfer(assembled, target, mode, delimiter, workspace)

    # -- stdout-only ------------------------------------------------------- #

    def _commit_stdout(self, location: WorkspaceLocation, delimiter: str) -> None:
        workspace = location.path
        assembled = self._assemble(workspace, STDOUT_CONTENT_NAME, delimiter, "stdout")
        if assembled is None:
            return  # Section 7.9: nothing from the replies goes to stdout.
        try:
            self._stdout.write(assembled.read_bytes().decode("utf-8"))
            self._stdout.flush()
        except (OSError, ValueError) as exc:
            raise WorkspaceCommitError(
                f"could not write to the stdout sink: {exc}; workspace: {workspace}"
            ) from exc

    # -- shared ------------------------------------------------------------ #

    @staticmethod
    def _assemble(workspace: Path, name: str, delimiter: str, target: str) -> Path | None:
        try:
            return assemble(workspace, name, delimiter)
        except OSError as exc:
            raise WorkspaceCommitError(
                f"Assembly failed for target {target}: {exc}; workspace: {workspace}"
            ) from exc

    @staticmethod
    def _preflight_exclusive(targets: list[Path], workspace: Path) -> None:
        """Section 7.1: any existing target aborts before the first rename."""
        existing = [target for target in targets if target.exists()]
        if existing:
            shown = ", ".join(str(path) for path in existing)
            raise WorkspaceCommitError(
                f"output_mode x: target already exists: {shown}; workspace: {workspace}"
            )

    @staticmethod
    def _transfer(source: Path, target: Path, mode: str, delimiter: str, workspace: Path) -> None:
        """One file per mode (Sections 7.1-7.3). The first failure stops the commit."""
        try:
            if mode == "a":
                _append_block(source, target, delimiter)
            elif mode == "w":
                source.replace(target)
            else:
                source.rename(target)
        except (OSError, ValueError) as exc:
            raise WorkspaceCommitError(
                f"could not commit to {target}: {exc}; workspace: {workspace}"
            ) from exc

    @staticmethod
    def _remove(workspace: Path) -> None:
        if not workspace.is_dir():
            return
        try:
            shutil.rmtree(workspace)
        except OSError as exc:
            # The sink is already complete; only the scratch copy is left over.
            logger.warning("Could not remove workspace %s: %s", workspace, exc)


# --------------------------------------------------------------------------- #
# Simulate boards (outside the staging profile, Section 2.2)
# --------------------------------------------------------------------------- #


def commit_assembled_output(
    path: Path, mode: str, body: str, delimiter: str, *, allow_empty: bool = False
) -> None:
    """Write a simulate board directly to one target, honouring -m."""
    if not allow_empty and (body or "").strip() == "":
        return
    if mode == "a":
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > 0:
            text = path.read_text(encoding="utf-8") + delimiter + body
        else:
            text = body
        write_or_append_lines_to_unique_file(path, "w", [text])
        return
    write_or_append_lines_to_unique_file(path, mode, [body])
