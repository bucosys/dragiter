# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Staging workspace and commit, ``design/specs/spec-stag-staging.md``.

Tests are grouped by the validation phases of STAG Appendix B (P, G, X, L, I);
each test names the acceptance criteria (``STAG-NN``) it covers.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import os
from pathlib import Path
import re
import time

import pytest
from support import blank_parameter_groups

from dragiter.application.config.configuration_validator import (
    ConfigurationValidator,
    ConfigurationValidatorError,
)
from dragiter.application.pipeline.chat_manager import ChatManager
from dragiter.application.pipeline.output_writer import OutputWriter
from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatMessage, ChatSession, ChatSessions
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.context_validation_report import ContextValidationReport
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.resources import Resources
from dragiter.domain.models.settings import ValueOrigin
from dragiter.infrastructure.cli.markdown_result_board import MarkdownResultBoard
from dragiter.infrastructure.cli.null_session_board import NullSessionBoard
from dragiter.infrastructure.cli.stderr_session_board import StderrSessionBoard
from dragiter.infrastructure.io.filename_utils import format_timestamp_ns
from dragiter.infrastructure.io.workspace_service import (
    DIR_STAGING_PREFIX,
    EXCLUSIVE_RUNTIME_NOTICE,
    FILE_STAGING_PREFIX,
    RESUME_ADOPTION_NOTICE,
    STDOUT_CONTENT_NAME,
    STDOUT_STAGING_PREFIX,
    NewestWorkspaceSeeder,
    NullWorkspaceSeeder,
    WorkspaceCommitError,
    WorkspaceCommitService,
    WorkspaceConflictError,
    WorkspaceError,
    WorkspaceLayout,
    WorkspacePersistenceService,
    WorkspaceRun,
    assemble,
    list_shards,
    shard_name,
    user_temp_directory,
)
from dragiter.infrastructure.llm.mockai_service import MockAIService

DELIM = "\n---\n"
PID = os.getpid()


# --------------------------------------------------------------------------- #
# Fixtures (STAG Appendix B, "Shared fixtures")
# --------------------------------------------------------------------------- #


@dataclass
class Env:
    cwd: Path
    user_temp: Path
    dir: Path
    layout: WorkspaceLayout

    @property
    def file(self) -> Path:
        return self.dir / "report.md"

    def staging_dirs(self, root: Path) -> list[Path]:
        return sorted(p for p in root.iterdir() if p.name.startswith(".tmp_staging_"))


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Env:
    cwd = tmp_path / "cwd"
    user_temp = tmp_path / "usertemp"
    out = tmp_path / "out"
    for path in (cwd, user_temp, out):
        path.mkdir()
    monkeypatch.chdir(cwd)
    return Env(cwd, user_temp, out, WorkspaceLayout(pid=PID, user_temp=user_temp))


def _groups(mode: str = "w", *, directory: Path | None = None, file: Path | None = None):
    groups = blank_parameter_groups()
    groups["op"].output_mode_string_setting.set(mode, ValueOrigin.CLI)
    if directory is not None:
        groups["op"].output_directory_path_setting.set(directory, ValueOrigin.CLI)
    if file is not None:
        groups["op"].output_file_path_setting.set(file, ValueOrigin.CLI)
    return groups


def _prompt(schema: str = "{CHUNK_FILE_NAME}.txt") -> PromptTemplate:
    return PromptTemplate("", "", "", "", 0.0, False, schema, DELIM)


def _session(name: str, loop_id: int = 1) -> ChatSession:
    return ChatSession(
        input_chat_message_list=[ChatMessage(role="user", content="ask")],
        chunk=Chunk(1, name, "sec01", 1, True, "hello"),
        loop_item={"LOOP_CONTENT": "ask", "LOOP_NUM_ID": loop_id},
    )


def _sessions(count: int) -> list[ChatSession]:
    return [_session(f"s{index}.md", index) for index in range(1, count + 1)]


def _result(text: str) -> ChatResult:
    result = ChatResult(finish_reason="stop")
    result.output_chat_message.content = text
    return result


def _service(layout: WorkspaceLayout) -> WorkspacePersistenceService:
    """Ordinary, --resume-less service: NullWorkspaceSeeder on both slots."""
    return WorkspacePersistenceService(layout, NullWorkspaceSeeder(), NullWorkspaceSeeder())


def _persist(
    env: Env, groups, prompt: PromptTemplate, texts: list[str], *, ep=None
) -> WorkspaceRun:
    sessions = _sessions(len(texts))
    run = _service(env.layout).open(groups["op"], prompt, sessions, ep or groups["ep"])
    for index, (session, text) in enumerate(zip(sessions, texts, strict=True), start=1):
        run.persist(index, session, _result(text))
    return run


def _commit(env: Env, groups, prompt: PromptTemplate, count: int, stdout: StringIO | None = None):
    service = WorkspaceCommitService(env.layout, stdout if stdout is not None else StringIO())
    service.commit(groups["op"], prompt, _sessions(count))


def _shard_names(run: WorkspaceRun) -> list[str]:
    return [shard.name for shard in list_shards(run.path)]


# --------------------------------------------------------------------------- #
# Phase P - parents, before anything is persisted
# --------------------------------------------------------------------------- #


def test_p1_missing_dir_aborts_without_workspace(env: Env) -> None:
    """STAG-01."""
    missing = env.dir / "missing"
    with pytest.raises(WorkspaceError, match="missing or not a directory"):
        _persist(env, _groups(directory=missing), _prompt(), ["A"])
    assert not missing.exists()
    assert env.staging_dirs(env.dir) == []


def test_p2_dir_is_a_file_aborts(env: Env) -> None:
    """STAG-01."""
    not_a_dir = env.dir / "plain"
    not_a_dir.write_text("x", encoding="utf-8")
    with pytest.raises(WorkspaceError):
        _persist(env, _groups(directory=not_a_dir), _prompt(), ["A"])
    assert env.staging_dirs(env.dir) == []


def test_p3_missing_file_parent_aborts(env: Env) -> None:
    """STAG-03."""
    target = env.dir / "nope" / "report.md"
    with pytest.raises(WorkspaceError):
        _persist(env, _groups(file=target), _prompt(), ["A"])
    assert not target.parent.exists()


def test_p4_unusable_tmpdir_aborts_stdout(env: Env, tmp_path: Path) -> None:
    """STAG-33: a set but unusable $TMPDIR is not silently replaced."""
    unusable = tmp_path / "no-such-tmp"
    user_temp = user_temp_directory({"TMPDIR": str(unusable)})
    assert user_temp == unusable
    layout = WorkspaceLayout(pid=PID, user_temp=user_temp)
    groups = _groups()
    with pytest.raises(WorkspaceError, match="user temp"):
        _service(layout).open(groups["op"], _prompt(), _sessions(1), groups["ep"])
    assert env.staging_dirs(env.cwd) == []
    assert not unusable.exists()


def test_p1_p3_validator_rejects_missing_sink_parents(env: Env) -> None:
    """STAG-01 and STAG-03, enforced at parametrisation."""
    groups = _groups(directory=env.dir / "missing")
    groups["ep"].simulate_bool_setting.set(True, ValueOrigin.CLI)
    groups["ip"].task_string_setting.set("do it", ValueOrigin.CLI)
    with pytest.raises(ConfigurationValidatorError, match="missing or not a directory"):
        ConfigurationValidator().run(
            groups["aisp"], groups["lp"], groups["ep"], groups["ip"], groups["op"], groups["wp"]
        )


def test_stag_06_o_and_big_o_are_mutually_exclusive(env: Env) -> None:
    """STAG-06: refused at parametrisation, before any path check."""
    groups = _groups(directory=env.dir / "missing", file=env.cwd / "missing" / "x.md")
    with pytest.raises(ConfigurationValidatorError, match="mutually exclusive") as info:
        ConfigurationValidator().run(
            groups["aisp"], groups["lp"], groups["ep"], groups["ip"], groups["op"], groups["wp"]
        )
    assert "not a directory" not in str(info.value)
    with pytest.raises(WorkspaceError, match="mutually exclusive"):
        env.layout.locate(groups["op"])


# --------------------------------------------------------------------------- #
# Phase G - happy path per sink
# --------------------------------------------------------------------------- #


def test_g1_directory_sink(env: Env) -> None:
    """STAG-02, STAG-05, STAG-07, STAG-09, STAG-20."""
    groups = _groups("w", directory=env.dir)
    prompt = _prompt()
    run = _persist(env, groups, prompt, ["A", "B"])

    assert run.path == env.dir / f"{DIR_STAGING_PREFIX}{PID}"
    assert _shard_names(run) == ["res000001", "res000002"]
    assert [p.read_text(encoding="utf-8") for p in list_shards(run.path)] == ["A", "B"]
    assert env.staging_dirs(env.cwd) == []
    assert env.staging_dirs(env.user_temp) == []

    _commit(env, groups, prompt, 2)
    assert (env.dir / "s1.md.txt").read_text(encoding="utf-8") == "A"
    assert (env.dir / "s2.md.txt").read_text(encoding="utf-8") == "B"
    assert env.staging_dirs(env.dir) == []


def test_g1x_directory_sink_exclusive_create_succeeds(env: Env) -> None:
    """STAG-18."""
    groups = _groups("x", directory=env.dir)
    prompt = _prompt()
    run = _persist(env, groups, prompt, ["A", "B"])

    _commit(env, groups, prompt, 2)
    assert (env.dir / "s1.md.txt").read_text(encoding="utf-8") == "A"
    assert (env.dir / "s2.md.txt").read_text(encoding="utf-8") == "B"
    assert env.staging_dirs(env.dir) == []
    assert not run.path.exists()


def test_g2_file_sink(env: Env) -> None:
    """STAG-04, STAG-11, STAG-12, STAG-15, STAG-24."""
    groups = _groups("w", file=env.file)
    prompt = _prompt()
    run = _persist(env, groups, prompt, ["A", "B"])

    assert run.path == env.dir / f"{FILE_STAGING_PREFIX}{PID}"
    assert _shard_names(run) == ["res000001", "res000002"]
    assert not (run.path / env.file.name).exists()

    # Cut between Assembly and commit.
    assembled = assemble(run.path, env.file.name, DELIM)
    assert assembled is not None
    assert assembled.read_text(encoding="utf-8") == f"A{DELIM}B"
    assert _shard_names(run) == ["res000001", "res000002"]
    assembled.unlink()

    _commit(env, groups, prompt, 2)
    assert env.file.read_text(encoding="utf-8") == f"A{DELIM}B"
    assert env.staging_dirs(env.dir) == []
    assert env.staging_dirs(env.user_temp) == []


def test_g3_stdout_sink(env: Env) -> None:
    """STAG-14, STAG-30, STAG-31, STAG-32, STAG-34."""
    groups = _groups("x")
    prompt = _prompt()
    run = _persist(env, groups, prompt, ["A", "B"])

    assert run.path == env.user_temp / f"{STDOUT_STAGING_PREFIX}{PID}"
    assert _shard_names(run) == ["res000001", "res000002"]
    assert not (run.path / STDOUT_CONTENT_NAME).exists()
    assert env.staging_dirs(env.cwd) == []

    out = StringIO()
    _commit(env, groups, prompt, 2, out)
    assert out.getvalue() == f"A{DELIM}B"
    assert env.staging_dirs(env.user_temp) == []


def test_tmpdir_is_used_as_user_temp(tmp_path: Path) -> None:
    """STAG-32."""
    assert user_temp_directory({"TMPDIR": str(tmp_path)}) == tmp_path


# --------------------------------------------------------------------------- #
# Persist details (STAG Section 6)
# --------------------------------------------------------------------------- #


def test_empty_completion_still_produces_shard(env: Env) -> None:
    """STAG-08."""
    run = _persist(env, _groups(file=env.file), _prompt(), ["", "A"])
    shards = list_shards(run.path)
    assert [p.name for p in shards] == ["res000001", "res000002"]
    assert shards[0].stat().st_size == 0


def test_shard_content_is_unchanged(env: Env) -> None:
    """STAG-07: exactly the completion text, no stripping, no newline added."""
    text = "  lead\r\ntrail  \n"
    run = _persist(env, _groups(directory=env.dir), _prompt(), [text])
    assert list_shards(run.path)[0].read_bytes() == text.encode("utf-8")


def test_shard_number_overflow_is_an_error() -> None:
    """STAG Section 6.1: no silent widening."""
    assert shard_name(999_999) == "res999999"
    with pytest.raises(WorkspaceError):
        shard_name(1_000_000)


def test_existing_own_workspace_is_not_reused(env: Env) -> None:
    (env.dir / f"{DIR_STAGING_PREFIX}{PID}").mkdir()
    with pytest.raises(WorkspaceError, match="already exists"):
        _persist(env, _groups(directory=env.dir), _prompt(), ["A"])


# --------------------------------------------------------------------------- #
# Phase X - exclusive and move failures
# --------------------------------------------------------------------------- #


def test_x1_existing_file_with_x_aborts_before_chat(env: Env) -> None:
    env.file.write_text("old", encoding="utf-8")
    with pytest.raises(WorkspaceConflictError):
        _persist(env, _groups("x", file=env.file), _prompt(), ["A"])
    assert env.staging_dirs(env.dir) == []


def test_x2_existing_planned_name_with_x_aborts(env: Env) -> None:
    (env.dir / "s1.md.txt").write_text("old", encoding="utf-8")
    with pytest.raises(WorkspaceConflictError, match=re.escape("s1.md.txt")):
        _persist(env, _groups("x", directory=env.dir), _prompt(), ["A"])
    assert env.staging_dirs(env.dir) == []


@pytest.mark.parametrize("mode", ["x", "w", "a"])
def test_x3_duplicate_planned_names_abort_in_every_mode(env: Env, mode: str) -> None:
    """STAG-28."""
    groups = _groups(mode, directory=env.dir)
    sessions = [_session("same.md", 1), _session("same.md", 2)]
    with pytest.raises(WorkspaceConflictError):
        _service(env.layout).open(groups["op"], _prompt(), sessions, groups["ep"])
    assert env.staging_dirs(env.dir) == []


def test_x4_target_appearing_before_commit_blocks_x(env: Env) -> None:
    """STAG-19 and STAG Section 9."""
    groups = _groups("x", directory=env.dir)
    prompt = _prompt()
    run = _persist(env, groups, prompt, ["A", "B"])
    late = env.dir / "s2.md.txt"
    late.write_text("late", encoding="utf-8")

    with pytest.raises(WorkspaceCommitError) as info:
        _commit(env, groups, prompt, 2)
    assert str(late) in str(info.value)
    assert str(run.path) in str(info.value)
    assert not (env.dir / "s1.md.txt").exists()
    assert late.read_text(encoding="utf-8") == "late"
    assert _shard_names(run) == ["res000001", "res000002"]


def test_x5_second_rename_failure_stops_the_commit(env: Env) -> None:
    """STAG-21."""
    groups = _groups("w", directory=env.dir)
    prompt = _prompt()
    run = _persist(env, groups, prompt, ["A", "B"])
    blocker = env.dir / "s2.md.txt"
    blocker.mkdir()
    (blocker / "keep").write_text("x", encoding="utf-8")

    with pytest.raises(WorkspaceCommitError, match=re.escape(str(run.path))):
        _commit(env, groups, prompt, 2)
    assert (env.dir / "s1.md.txt").read_text(encoding="utf-8") == "A"
    assert _shard_names(run) == ["res000002"]


def test_x6_file_x_missing_target_is_renamed(env: Env) -> None:
    """STAG-22."""
    groups = _groups("x", file=env.file)
    prompt = _prompt()
    _persist(env, groups, prompt, ["A"])
    _commit(env, groups, prompt, 1)
    assert env.file.read_text(encoding="utf-8") == "A"
    assert env.staging_dirs(env.dir) == []


def test_x7_file_x_existing_target_at_commit_keeps_workspace(env: Env) -> None:
    """STAG-23."""
    groups = _groups("x", file=env.file)
    prompt = _prompt()
    run = _persist(env, groups, prompt, ["A"])
    env.file.write_text("old", encoding="utf-8")

    with pytest.raises(WorkspaceCommitError) as info:
        _commit(env, groups, prompt, 1)
    assert str(env.file) in str(info.value) and str(run.path) in str(info.value)
    assert env.file.read_text(encoding="utf-8") == "old"
    assert run.path.is_dir()


def test_stdout_write_failure_keeps_workspace(env: Env) -> None:
    """STAG-36."""

    class _Broken(StringIO):
        def write(self, text: str) -> int:
            raise OSError("pipe closed")

    groups = _groups("x")
    prompt = _prompt()
    run = _persist(env, groups, prompt, ["A"])
    with pytest.raises(WorkspaceCommitError, match="stdout") as info:
        _commit(env, groups, prompt, 1, _Broken())
    assert str(run.path) in str(info.value)
    assert run.path.is_dir()


# --------------------------------------------------------------------------- #
# Append (STAG Section 7.3)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("before", "expected"),
    [(None, "A"), ("", "A"), ("old", f"old{DELIM}A")],
    ids=["missing", "empty", "non-empty"],
)
def test_file_append_delimiter_rule(env: Env, before: str | None, expected: str) -> None:
    """STAG-25."""
    if before is not None:
        env.file.write_text(before, encoding="utf-8")
    groups = _groups("a", file=env.file)
    prompt = _prompt()
    _persist(env, groups, prompt, ["A"])
    _commit(env, groups, prompt, 1)
    assert env.file.read_text(encoding="utf-8") == expected
    assert env.staging_dirs(env.dir) == []


# --------------------------------------------------------------------------- #
# Phase L - empty semantics
# --------------------------------------------------------------------------- #


def test_l1_file_skips_empty_shard(env: Env) -> None:
    groups = _groups("w", file=env.file)
    prompt = _prompt()
    _persist(env, groups, prompt, ["", "A"])
    _commit(env, groups, prompt, 2)
    assert env.file.read_text(encoding="utf-8") == "A"


def test_l2_file_only_empty_creates_nothing(env: Env) -> None:
    """STAG-13 and STAG Section 7.8."""
    groups = _groups("w", file=env.file)
    prompt = _prompt()
    run = _persist(env, groups, prompt, [""])
    assert assemble(run.path, env.file.name, DELIM) is None
    _commit(env, groups, prompt, 1)
    assert not env.file.exists()
    assert env.staging_dirs(env.dir) == []


def test_l3_stdout_only_empty_prints_nothing(env: Env) -> None:
    """STAG-35."""
    groups = _groups("x")
    prompt = _prompt()
    _persist(env, groups, prompt, [""])
    out = StringIO()
    _commit(env, groups, prompt, 1, out)
    assert out.getvalue() == ""
    assert env.staging_dirs(env.user_temp) == []


def test_l4_directory_keeps_empty_slot(env: Env) -> None:
    """STAG-16."""
    groups = _groups("w", directory=env.dir)
    prompt = _prompt()
    _persist(env, groups, prompt, ["A", ""])
    _commit(env, groups, prompt, 2)
    empty = env.dir / "s2.md.txt"
    assert empty.exists() and empty.stat().st_size == 0


def test_l5_directory_append_empty_leaves_target(env: Env) -> None:
    """STAG-17."""
    target = env.dir / "s1.md.txt"
    target.write_text("old", encoding="utf-8")
    groups = _groups("a", directory=env.dir)
    prompt = _prompt()
    _persist(env, groups, prompt, [""])
    _commit(env, groups, prompt, 1)
    assert target.read_text(encoding="utf-8") == "old"


# --------------------------------------------------------------------------- #
# Phase I - isolation and TIMESTAMP
# --------------------------------------------------------------------------- #


def test_i4_foreign_workspace_survives_cleanup(env: Env) -> None:
    """STAG-29."""
    foreign = env.dir / f"{DIR_STAGING_PREFIX}1"
    foreign.mkdir()
    groups = _groups("w", directory=env.dir)
    prompt = _prompt()
    _persist(env, groups, prompt, ["A"])
    _commit(env, groups, prompt, 1)
    assert foreign.is_dir()


def test_i5_timestamp_skips_early_check_and_uses_shard_mtime(
    env: Env, capsys: pytest.CaptureFixture[str]
) -> None:
    """STAG-10, STAG-26, STAG-27."""
    (env.dir / "keep.txt").write_text("x", encoding="utf-8")
    groups = _groups("x", directory=env.dir)
    prompt = _prompt("out_{TIMESTAMP}.txt")
    run = _persist(env, groups, prompt, ["A"])
    assert EXCLUSIVE_RUNTIME_NOTICE in capsys.readouterr().err

    shard = list_shards(run.path)[0]
    fixed_ns = 1_700_000_000_123_456_789
    os.utime(shard, ns=(fixed_ns, fixed_ns))

    _commit(env, groups, prompt, 1)
    expected = env.dir / f"out_{format_timestamp_ns(fixed_ns)}.txt"
    assert expected.read_text(encoding="utf-8") == "A"


# --------------------------------------------------------------------------- #
# Phase R - Resume (--resume, -O only), independent of P-I
# --------------------------------------------------------------------------- #


def _resume_service(layout: WorkspaceLayout) -> WorkspacePersistenceService:
    return WorkspacePersistenceService(layout, NullWorkspaceSeeder(), NewestWorkspaceSeeder())


def test_r1_adopts_newest_sibling_workspace_shards(
    env: Env, capsys: pytest.CaptureFixture[str]
) -> None:
    """STAG-37, STAG-38, STAG-39."""
    source = env.dir / f"{DIR_STAGING_PREFIX}999001"
    source.mkdir()
    (source / shard_name(1)).write_bytes(b"A")
    (source / shard_name(2)).write_bytes(b"B")

    groups = _groups("w", directory=env.dir)
    groups["ep"].resume_bool_setting.set(True, ValueOrigin.CLI)
    run = _resume_service(env.layout).open(groups["op"], _prompt(), _sessions(2), groups["ep"])

    assert not source.exists()  # STAG-39: emptied source is removed
    shards = list_shards(run.path)
    assert [shard.name for shard in shards] == [shard_name(1), shard_name(2)]  # STAG-38: order
    assert (run.path / shard_name(1)).read_bytes() == b"A"
    assert (run.path / shard_name(2)).read_bytes() == b"B"
    assert (RESUME_ADOPTION_NOTICE % (2, source)) in capsys.readouterr().err


def test_r2_resume_without_a_candidate_is_an_ordinary_fresh_run(env: Env) -> None:
    """STAG-40."""
    groups = _groups("w", directory=env.dir)
    groups["ep"].resume_bool_setting.set(True, ValueOrigin.CLI)
    run = _resume_service(env.layout).open(groups["op"], _prompt(), _sessions(1), groups["ep"])
    assert list_shards(run.path) == []


def test_r3_only_the_newest_sibling_workspace_is_adopted(env: Env) -> None:
    """STAG-41."""
    older = env.dir / f"{DIR_STAGING_PREFIX}999001"
    newer = env.dir / f"{DIR_STAGING_PREFIX}999002"
    older.mkdir()
    newer.mkdir()
    (older / shard_name(1)).write_bytes(b"old")
    (newer / shard_name(1)).write_bytes(b"new")
    # Force a clear mtime ordering, independent of filesystem timestamp
    # resolution or the speed of the two mkdir() calls above.
    now = time.time()
    os.utime(older, (now - 10, now - 10))
    os.utime(newer, (now, now))

    groups = _groups("w", directory=env.dir)
    groups["ep"].resume_bool_setting.set(True, ValueOrigin.CLI)
    run = _resume_service(env.layout).open(groups["op"], _prompt(), _sessions(1), groups["ep"])

    assert not newer.exists()
    assert older.is_dir()  # untouched; STAG-29 still applies to it
    assert (older / shard_name(1)).read_bytes() == b"old"
    assert (run.path / shard_name(1)).read_bytes() == b"new"


def test_r4_reuse_advances_the_counter_one_session_at_a_time(env: Env) -> None:
    """STAG-42."""
    source = env.dir / f"{DIR_STAGING_PREFIX}999001"
    source.mkdir()
    # Sessions 1, 2 and 4 already have shards - as if a partially committed
    # predecessor run had already renamed session 3's shard onto its final
    # name before aborting (STAG Section 5.4's limits): session 3 is a gap.
    for number in (1, 2, 4):
        (source / shard_name(number)).write_bytes(f"s{number}".encode())

    groups = _groups("w", directory=env.dir)
    groups["ep"].resume_bool_setting.set(True, ValueOrigin.CLI)
    run = _resume_service(env.layout).open(groups["op"], _prompt(), _sessions(5), groups["ep"])

    assert run.reuse(1) is True
    assert run.reuse(2) is True
    assert run.reuse(3) is False  # the gap: must be re-persisted, not skipped
    run.persist(3, _session("s3.md", 3), _result("regenerated"))
    assert run.reuse(4) is True  # unaffected by the gap: still its own number
    assert run.reuse(5) is False

    assert (run.path / shard_name(3)).read_bytes() == b"regenerated"
    assert (run.path / shard_name(4)).read_bytes() == b"s4"


def test_file_name_colliding_with_shard_scheme_is_rejected(env: Env) -> None:
    target = env.dir / "res000001"
    groups = _groups("w", file=target)
    prompt = _prompt()
    run = _persist(env, groups, prompt, ["A"])
    with pytest.raises(WorkspaceCommitError, match="shard naming scheme"):
        _commit(env, groups, prompt, 1)
    assert run.path.is_dir()


# --------------------------------------------------------------------------- #
# Through the workers: ChatManager persists, OutputWriter commits
# --------------------------------------------------------------------------- #


class _LiveEcho:
    """Live LLM double: returns the chunk file name as reply text."""

    def process_query(self, aisp, lp, chat_session, progress=None) -> ChatResult:
        return _result(chat_session.chunk.filename.upper())


def test_workers_share_one_workspace_via_layout(env: Env) -> None:
    groups = _groups("w", directory=env.dir)
    prompt = _prompt()
    sessions = ChatSessions(_sessions(2))
    manager = ChatManager(
        _LiveEcho(),
        MockAIService(),
        StderrSessionBoard(StringIO(), interactive=False),
        NullSessionBoard(),
        _service(env.layout),
        MarkdownResultBoard(),
    )
    context_report = ContextValidationReport(is_valid=True, total_tokens=0, max_tokens_limit=0)
    resources = Resources()
    manager.run(
        groups["aisp"],
        groups["lp"],
        groups["ep"],
        sessions,
        groups["op"],
        Material([]),
        Loop(),
        context_report,
        resources,
        prompt,
    )
    assert (env.dir / f"{DIR_STAGING_PREFIX}{PID}").is_dir()

    OutputWriter(WorkspaceCommitService(env.layout, StringIO())).run(
        sessions,
        groups["op"],
        prompt,
    )
    assert (env.dir / "s1.md.txt").read_text(encoding="utf-8") == "S1.MD"
    assert (env.dir / "s2.md.txt").read_text(encoding="utf-8") == "S2.MD"
    assert env.staging_dirs(env.dir) == []


def test_output_writer_commits_regardless_of_content_origin(env: Env) -> None:
    """
    OutputWriter no longer distinguishes live from simulate (it takes no `ep` or
    `ChatResults` to do so): it always commits whatever ChatManager persisted,
    live reply or a simulate session's board+request alike.
    """
    groups = _groups("w")
    prompt = _prompt()
    _persist(env, groups, prompt, ["mock"])
    out = StringIO()
    OutputWriter(WorkspaceCommitService(env.layout, out)).run(
        ChatSessions(_sessions(1)),
        groups["op"],
        prompt,
    )
    assert out.getvalue() == "mock"
    assert env.staging_dirs(env.user_temp) == []
