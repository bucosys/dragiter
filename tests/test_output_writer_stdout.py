# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold
"""Stdout is only the default sink when neither -o nor -O is set."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest
from support import blank_parameter_groups

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
from dragiter.infrastructure.io.workspace_service import (
    WorkspaceCommitService,
    WorkspaceError,
    WorkspaceLayout,
    WorkspacePersistenceService,
)
from dragiter.infrastructure.llm.mockai_service import MockAIService

RESULT_TEXT = "unique-result-payload-stdout-routing"


def _session() -> ChatSession:
    return ChatSession(
        input_chat_message_list=[ChatMessage(role="user", content="ask")],
        chunk=Chunk(1, "note.md", "sec01", 1, True, "hello"),
        loop_item={"LOOP_CONTENT": "ask", "LOOP_NUM_ID": 1},
    )


def _run(
    groups,
    user_temp: Path,
    *,
    content: str = RESULT_TEXT,
    filename_schema: str = "result.txt",
) -> None:
    """Live path: persist one shard directly, as ChatManager would, then commit it."""
    groups["op"].output_mode_string_setting.set("w", ValueOrigin.CLI)
    session = _session()
    result = ChatResult(finish_reason="stop")
    result.output_chat_message.content = content
    prompt = PromptTemplate("", "", "", "", 0.0, False, filename_schema, "\n\n")
    layout = WorkspaceLayout(pid=os.getpid(), user_temp=user_temp)
    run = WorkspacePersistenceService(layout).open(groups["op"], prompt, [session])
    run.persist(1, session, result)
    OutputWriter(WorkspaceCommitService(layout, sys.stdout)).run(
        ChatSessions([session]), groups["op"], prompt,
    )


def _run_simulate(groups, user_temp: Path, *, result_board=None) -> None:
    """Simulate path: run the real ChatManager so it builds and persists the board
    and complete request itself, then commit exactly like the live path."""
    groups["ep"].simulate_bool_setting.set(True, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("w", ValueOrigin.CLI)
    session = _session()
    prompt = PromptTemplate("", "", "", "", 0.0, False, "result.txt", "\n\n")
    layout = WorkspaceLayout(pid=os.getpid(), user_temp=user_temp)
    manager = ChatManager(
        MockAIService(),  # llm_service: never invoked, simulate always picks mock
        MockAIService(),
        NullSessionBoard(),
        NullSessionBoard(),
        WorkspacePersistenceService(layout),
        result_board or MarkdownResultBoard(),
    )
    sessions = ChatSessions([session])
    manager.run(
        groups["aisp"],
        groups["lp"],
        groups["ep"],
        sessions,
        groups["op"],
        Material([session.chunk]),
        Loop([{"LOOP_CONTENT": "ask", "LOOP_NUM_ID": 1}]),
        ContextValidationReport(is_valid=True, total_tokens=0, max_tokens_limit=0),
        Resources(),
        prompt,
    )
    OutputWriter(WorkspaceCommitService(layout, sys.stdout)).run(
        sessions, groups["op"], prompt,
    )


def test_live_result_echoes_on_stdout_when_no_file_sink(tmp_path: Path, capsys) -> None:
    """OUTP-08."""
    groups = blank_parameter_groups()
    _run(groups, tmp_path)
    captured = capsys.readouterr()
    assert RESULT_TEXT in captured.out
    assert captured.out.strip() == RESULT_TEXT


def test_live_result_not_echoed_when_output_file_is_set(tmp_path: Path, capsys) -> None:
    """OUTP-09."""
    groups = blank_parameter_groups()
    target = tmp_path / "out.txt"
    groups["op"].output_file_path_setting.set(target, ValueOrigin.CLI)
    _run(groups, tmp_path)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert RESULT_TEXT in target.read_text(encoding="utf-8")


def test_live_result_not_echoed_when_output_directory_is_set(
    tmp_path: Path, capsys
) -> None:
    """OUTP-10."""
    groups = blank_parameter_groups()
    groups["op"].output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    _run(groups, tmp_path, filename_schema="{CHUNK_FILE_NAME}.txt")
    captured = capsys.readouterr()
    assert captured.out == ""
    written = [p for p in tmp_path.iterdir() if p.is_file()]
    assert written
    assert RESULT_TEXT in written[0].read_text(encoding="utf-8")


def test_both_file_sinks_are_rejected(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    out_dir = tmp_path / "many"
    out_dir.mkdir()
    groups["op"].output_file_path_setting.set(tmp_path / "single.txt", ValueOrigin.CLI)
    groups["op"].output_directory_path_setting.set(out_dir, ValueOrigin.CLI)
    with pytest.raises(WorkspaceError, match="mutually exclusive"):
        _run(groups, tmp_path, filename_schema="{CHUNK_FILE_NAME}.txt")


def test_simulate_board_stays_on_stdout_without_file_sink(tmp_path: Path, capsys) -> None:
    """OUTP-11, SIMU-07."""
    groups = blank_parameter_groups()
    groups["aisp"].model_name_string_setting.set("mock-model", ValueOrigin.CLI)
    _run_simulate(groups, tmp_path)
    captured = capsys.readouterr()
    assert "| DRAGITER" in captured.out
    # Unified with -o's content: the session's own board and complete request too.
    assert "ask" in captured.out


def test_simulate_board_not_echoed_when_output_file_is_set(
    tmp_path: Path, capsys
) -> None:
    """OUTP-12."""
    groups = blank_parameter_groups()
    groups["aisp"].model_name_string_setting.set("mock-model", ValueOrigin.CLI)
    target = tmp_path / "sim.md"
    groups["op"].output_file_path_setting.set(target, ValueOrigin.CLI)
    _run_simulate(groups, tmp_path)
    captured = capsys.readouterr()
    assert captured.out == ""
    body = target.read_text(encoding="utf-8")
    assert "| DRAGITER" in body
    assert "ask" in body


class _FixedResultBoard:
    def run_board(self, *args, frame: bool = True, **kwargs) -> str:
        return "FIXED-RUN-BOARD"

    def session_board(self, *args, **kwargs) -> str:
        return "FIXED-SESSION-BOARD"

    def payload_table(self, chat_session) -> str:
        return "FIXED-PAYLOAD"

    def join(self, *sections: str) -> str:
        return "\n".join(sections)


def test_output_writer_uses_injected_result_board(tmp_path: Path, capsys) -> None:
    """SIMU-09. Result-board injection lives on ChatManager, which builds the
    content OutputWriter later just commits."""
    groups = blank_parameter_groups()
    groups["aisp"].model_name_string_setting.set("mock-model", ValueOrigin.CLI)
    _run_simulate(groups, tmp_path, result_board=_FixedResultBoard())
    captured = capsys.readouterr()
    assert "FIXED-RUN-BOARD" in captured.out
    assert "| DRAGITER" not in captured.out
