# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from __future__ import annotations

from io import StringIO
import os
from pathlib import Path

import pytest
from support import blank_parameter_groups

from dragiter.application.pipeline.chat_manager import ChatManager, ChatManagerError
from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.chat_sessions import ChatMessage, ChatSession, ChatSessions
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.context_validation_report import ContextValidationReport
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.resources import Resources
from dragiter.domain.models.settings import ValueOrigin
from dragiter.infrastructure.cli.null_session_board import NullSessionBoard
from dragiter.infrastructure.cli.stderr_session_board import (
    END_MARK,
    PULSE_MARKS,
    START_MARK,
    StderrSessionBoard,
)
from dragiter.infrastructure.io.null_persistence_service import NullPersistenceService
from dragiter.infrastructure.io.workspace_service import (
    DIR_STAGING_PREFIX,
    WorkspaceLayout,
    WorkspacePersistenceService,
    WorkspaceRun,
)
from dragiter.infrastructure.llm.mockai_service import MockAIService


def _pipeline_deps() -> tuple[Material, Loop, ContextValidationReport, Resources, PromptTemplate]:
    return (
        Material([]),
        Loop(),
        ContextValidationReport(is_valid=True, total_tokens=0, max_tokens_limit=0),
        Resources(),
        PromptTemplate(
            instruction="",
            first="",
            material="",
            synthesis="",
            temperature=0.0,
            sequential_processing=False,
            output_filename_schema="",
            output_delimiter="",
        ),
    )


def _session(name: str = "note.md") -> ChatSession:
    chunk = Chunk(
        num_id=1,
        filename=name,
        section_name="sec01",
        section_num_id=1,
        valid=True,
        content="hello",
    )
    return ChatSession(
        input_chat_message_list=[ChatMessage(role="user", content="ping")],
        chunk=chunk,
    )


def test_chat_manager_board_facts_keep_inapplicable_window_none() -> None:
    material, loop, report, resources, prompt = _pipeline_deps()
    report.is_valid = None
    report.max_tokens_limit = None
    report.max_session_tokens = None
    groups = blank_parameter_groups()
    facts = ChatManager._board_facts(
        groups["ep"],
        groups["op"],
        1,
        material,
        loop,
        report,
        resources,
        prompt,
    )
    assert facts["window_ok"] is None
    assert facts["peak_tokens"] is None
    assert facts["token_limit"] is None
    assert facts["peak_session"] is None


def test_start_and_end_board_prefix_every_line() -> None:
    stream = StringIO()
    board = StderrSessionBoard(stream, interactive=False)
    board.begin_run(
        model="qwen3:8b",
        sessions=2,
        simulate=False,
        sequential=True,
        chunks=10,
        source_files=1,
        valid_chunks=10,
        loop_items=0,
        total_chars=11119,
        pack_limit_chars=1500,
        pack_from="section",
        window_ok=True,
        peak_tokens=4562,
        token_limit=32000,
        peak_session=3,
        warning_count=0,
        output="/tmp/a.out",
    )
    result = ChatResult()
    result.finish_reason = "stop"
    result.duration_ms = 1000
    result.input_tokens = 10
    result.output_tokens = 4
    board.begin_session(1, 2, _session())
    board.end_session(result)
    board.end_run(ChatResults([result]))
    text = stream.getvalue()
    start_lines = [line for line in text.splitlines() if line.startswith(START_MARK)]
    end_lines = [line for line in text.splitlines() if line.startswith(END_MARK)]
    assert len(start_lines) >= 2
    assert all(line.startswith(f"{START_MARK} ") for line in start_lines)
    assert len(end_lines) >= 2
    assert all(line.startswith(f"{END_MARK} ") for line in end_lines)
    joined = "\n".join(start_lines)
    assert "sequential" in joined
    assert "chunks 10 / 1 files" in joined
    assert "pack 1,500 (section)" in joined
    assert "window yes" in joined
    assert "peak 4,562 / 32,000" in joined
    assert "output /tmp/a.out" in joined


def test_start_board_marks_window_na_when_estimate_missing() -> None:
    stream = StringIO()
    board = StderrSessionBoard(stream, interactive=False)
    board.begin_run(
        model="qwen3:8b",
        sessions=1,
        simulate=True,
        window_ok=None,
        peak_tokens=None,
        token_limit=None,
        peak_session=None,
        warning_count=0,
        output="none",
    )
    text = stream.getvalue()
    assert "window n/a" in text
    assert "peak -- / --" in text
    assert "peak at --" in text
    assert "window yes" not in text
    assert "peak 0 / 0" not in text


def test_clock_stays_on_one_line_and_throttles(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = StringIO()
    board = StderrSessionBoard(stream, interactive=True)
    clock = {"now": 0.0}
    monkeypatch.setattr(
        "dragiter.infrastructure.cli.stderr_session_board.time.monotonic",
        lambda: clock["now"],
    )
    board.begin_session(1, 1, _session())
    board.on_stream_chunk()
    clock["now"] = 9.0
    board.on_stream_chunk()
    clock["now"] = 10.0
    board.on_stream_chunk()
    raw = stream.getvalue()
    assert raw.count("\r") >= 2
    assert raw.count("\n") == 0
    assert PULSE_MARKS[1] in raw


def test_workspace_persistence_keeps_prior_sessions(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    op = groups["op"]
    op.output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    op.output_mode_string_setting.set("w", ValueOrigin.CLI)
    _, _, _, _, prompt = _pipeline_deps()
    prompt.output_filename_schema = "{CHUNK_FILE_NAME}"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    service = WorkspaceRun(workspace)
    first = ChatResult()
    first.output_chat_message.content = "one"
    second = ChatResult()
    second.output_chat_message.content = "two"
    service.persist(1, _session("a.md"), first)
    service.persist(2, _session("b.md"), second)
    stored = sorted(p for p in service.path.iterdir() if p.is_file())
    assert len(stored) == 2
    assert stored[0].read_text(encoding="utf-8") == "one"
    assert stored[1].read_text(encoding="utf-8") == "two"


class _FailOnSecond:
    def __init__(self) -> None:
        self.calls = 0

    def process_query(self, aisp, lp, session, progress=None):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("boom")
        result = ChatResult()
        result.output_chat_message.content = f"ok-{self.calls}"
        result.finish_reason = "stop"
        return result


def test_chat_manager_persists_before_a_later_failure(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    groups["aisp"].model_name_string_setting.set("test", ValueOrigin.CLI)
    groups["op"].output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("w", ValueOrigin.CLI)
    sessions = ChatSessions(session_list=[_session("a.md"), _session("b.md")])
    manager = ChatManager(
        _FailOnSecond(),
        MockAIService(),
        StderrSessionBoard(StringIO(), interactive=False),
        NullSessionBoard(),
        WorkspacePersistenceService(WorkspaceLayout(pid=os.getpid(), user_temp=tmp_path)),
    )
    deps = _pipeline_deps()
    deps[4].output_filename_schema = "{CHUNK_FILE_NAME}"
    with pytest.raises(ChatManagerError, match="boom"):
        manager.run(
            groups["aisp"],
            groups["lp"],
            groups["ep"],
            sessions,
            groups["op"],
            *deps,
        )
    staging = tmp_path / f"{DIR_STAGING_PREFIX}{os.getpid()}"
    saved = sorted(p for p in staging.iterdir() if p.is_file()) if staging.is_dir() else []
    assert staging.is_dir(), list(tmp_path.iterdir())
    assert len(saved) == 1
    assert saved[0].read_text(encoding="utf-8") == "ok-1"


def test_mock_does_not_emit_stream_chunks() -> None:
    class _Probe:
        def __init__(self) -> None:
            self.chunks = 0

        def on_stream_chunk(self) -> None:
            self.chunks += 1

        def abandon_session(self) -> None:
            return None

        def begin_run(self, **kwargs) -> None:
            return None

        def begin_session(self, index, total, session) -> None:
            return None

        def end_session(self, result) -> None:
            return None

        def end_run(self, results) -> None:
            return None

    groups = blank_parameter_groups()
    groups["aisp"].model_name_string_setting.set("mock", ValueOrigin.CLI)
    probe = _Probe()
    manager = ChatManager(
        MockAIService(),
        MockAIService(),
        verbose_board=probe,
        silent_board=probe,
        persistence=NullPersistenceService(),
    )
    sessions = ChatSessions(session_list=[_session()])
    manager.run(
        groups["aisp"],
        groups["lp"],
        groups["ep"],
        sessions,
        groups["op"],
        *_pipeline_deps(),
    )
    assert probe.chunks == 0


def test_chat_manager_rejects_missing_collaborator() -> None:
    """ADR-0000, rule 8: a missing dependency is an error, never a fallback."""
    with pytest.raises(TypeError, match="silent_board"):
        ChatManager(
            MockAIService(),
            MockAIService(),
            NullSessionBoard(),
            None,  # type: ignore[arg-type]
            NullPersistenceService(),
        )


def test_chat_manager_uses_silent_board_without_verbose(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    groups["aisp"].model_name_string_setting.set("mock", ValueOrigin.CLI)
    stream = StringIO()
    manager = ChatManager(
        MockAIService(),
        MockAIService(),
        StderrSessionBoard(stream, interactive=False),
        NullSessionBoard(),
        NullPersistenceService(),
    )
    manager.run(
        groups["aisp"],
        groups["lp"],
        groups["ep"],
        ChatSessions(session_list=[_session()]),
        groups["op"],
        *_pipeline_deps(),
    )
    assert stream.getvalue() == ""
