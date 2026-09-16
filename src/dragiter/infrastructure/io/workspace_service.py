# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import sys

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import OutputParameters
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.infrastructure.io.filename_utils import (
    format_output_filename,
    schema_has_runtime_tokens,
    sortable_timestamp,
)
from dragiter.infrastructure.io.io_services import write_or_append_lines_to_unique_file

logger = logging.getLogger(__name__)

DIR_STAGING_PREFIX = ".tmp_staging_dir_"
# Kept so older tests and docs that mention the file artefact still import.
FILE_STAGING_PREFIX = ".tmp_staging_file_"

EXCLUSIVE_RUNTIME_NOTICE = (
    "output_mode x: early name check skipped because output_filename_schema "
    "contains TIMESTAMP; exclusive create is enforced at commit."
)


class WorkspaceConflictError(Exception):
    """Raised when -m x would fail, before any completion call."""


def workspace_parent(op: OutputParameters) -> Path:
    if op.output_directory_path_setting.is_set:
        return Path(op.output_directory_path_setting.value)
    if op.output_file_path_setting.is_set:
        return Path(op.output_file_path_setting.value).parent
    return Path.cwd()


def dir_workspace_path(op: OutputParameters, pid: int | None = None) -> Path:
    ident = os.getpid() if pid is None else pid
    return workspace_parent(op) / f"{DIR_STAGING_PREFIX}{ident}"


def list_workspace_files(op: OutputParameters, pid: int | None = None) -> list[Path]:
    staging = dir_workspace_path(op, pid)
    if not staging.is_dir():
        return []
    return sorted(path for path in staging.iterdir() if path.is_file())


def join_workspace_text(
    op: OutputParameters, delimiter: str, pid: int | None = None
) -> str:
    parts = [path.read_text(encoding="utf-8") for path in list_workspace_files(op, pid)]
    return delimiter.join(parts)


def commit_assembled_output(
    path: Path, mode: str, body: str, delimiter: str, *, allow_empty: bool = False
) -> None:
    """Apply -m to one target."""
    if not allow_empty and (body or "").strip() == "":
        return
    if mode == "a":
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            text = path.read_text(encoding="utf-8") + delimiter + body
        else:
            text = body
        write_or_append_lines_to_unique_file(path, "w", [text])
        return
    write_or_append_lines_to_unique_file(path, mode, [body])


def cleanup_run_workspaces(op: OutputParameters, pid: int | None = None) -> None:
    path = dir_workspace_path(op, pid)
    try:
        if path.is_dir():
            shutil.rmtree(path)
    except OSError as exc:
        logger.warning("Could not remove workspace %s: %s", path, exc)


class WorkspacePersistenceService:
    """One staging directory. One timestamp file per completion, empty allowed."""

    def __init__(
        self,
        op: OutputParameters,
        prompt: PromptTemplate,
        pid: int | None = None,
    ) -> None:
        self._op = op
        self._prompt = prompt
        self._pid = os.getpid() if pid is None else pid
        self._mode = (op.output_mode_string_setting.value or "x").strip() or "x"
        self._schema = prompt.output_filename_schema or ""

    @property
    def dir_workspace(self) -> Path:
        return dir_workspace_path(self._op, self._pid)

    def check_exclusive(self, sessions: list[ChatSession]) -> None:
        if self._mode != "x":
            return
        conflicts: list[Path] = []

        if self._op.output_file_path_setting.is_set:
            target = Path(self._op.output_file_path_setting.value)
            if target.exists():
                conflicts.append(target)

        if self._op.output_directory_path_setting.is_set:
            target_dir = Path(self._op.output_directory_path_setting.value)
            if schema_has_runtime_tokens(self._schema):
                print(EXCLUSIVE_RUNTIME_NOTICE, file=sys.stderr)
            else:
                names = [
                    format_output_filename(
                        session.chunk,
                        session.loop_item,
                        index,
                        self._schema,
                    )
                    for index, session in enumerate(sessions, start=1)
                ]
                seen: set[str] = set()
                for name in names:
                    planned = target_dir / name
                    if name in seen or planned.exists():
                        conflicts.append(planned)
                    seen.add(name)

        if conflicts:
            shown = ", ".join(str(path) for path in conflicts)
            raise WorkspaceConflictError(
                f"output_mode x: refusing to start; target already exists: {shown}"
            )

    def prepare(self) -> None:
        self.dir_workspace.mkdir(parents=True, exist_ok=True)

    def persist(self, index: int, session: ChatSession, result: ChatResult) -> None:
        try:
            piece = result.output_chat_message.content or ""
            name = f"{sortable_timestamp()}.txt"
            (self.dir_workspace / name).write_text(piece, encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not persist session %s: %s", index, exc)
