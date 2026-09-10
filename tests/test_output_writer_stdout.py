# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold
"""Stdout is only the default sink when neither -o nor -O is set."""

from __future__ import annotations

from pathlib import Path

from support import blank_parameter_groups

from dragiter.application.pipeline.output_writer import OutputWriter
from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.chat_sessions import ChatMessage, ChatSession, ChatSessions
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.settings import ValueOrigin

RESULT_TEXT = "unique-result-payload-stdout-routing"


def _run(
    groups,
    *,
    simulate: bool = False,
    content: str = RESULT_TEXT,
    filename_schema: str = "result.txt",
) -> None:
    groups["ep"].simulate_bool_setting.set(simulate, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("w", ValueOrigin.CLI)
    chunk = Chunk(1, "note.md", "sec01", 1, True, "hello")
    session = ChatSession(
        input_chat_message_list=[ChatMessage(role="user", content="ask")],
        chunk=chunk,
        loop_item={"LOOP_CONTENT": "ask", "LOOP_NUM_ID": 1},
    )
    result = ChatResult(finish_reason="mock" if simulate else "stop")
    result.output_chat_message.content = content
    OutputWriter().run(
        ChatSessions([session]),
        ChatResults([result]),
        groups["op"],
        PromptTemplate("", "", "", "", 0.0, False, filename_schema, "\n\n"),
        groups["ep"],
        groups["aisp"],
        Material([chunk]),
        Loop([{"LOOP_CONTENT": "ask", "LOOP_NUM_ID": 1}]),
    )


def test_live_result_echoes_on_stdout_when_no_file_sink(capsys) -> None:
    groups = blank_parameter_groups()
    _run(groups, simulate=False)
    captured = capsys.readouterr()
    assert RESULT_TEXT in captured.out
    assert captured.out.strip() == RESULT_TEXT


def test_live_result_not_echoed_when_output_file_is_set(tmp_path: Path, capsys) -> None:
    groups = blank_parameter_groups()
    target = tmp_path / "out.txt"
    groups["op"].output_file_path_setting.set(target, ValueOrigin.CLI)
    _run(groups, simulate=False)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert RESULT_TEXT in target.read_text(encoding="utf-8")


def test_live_result_not_echoed_when_output_directory_is_set(
    tmp_path: Path, capsys
) -> None:
    groups = blank_parameter_groups()
    groups["op"].output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    _run(groups, simulate=False, filename_schema="{CHUNK_FILE_NAME}.txt")
    captured = capsys.readouterr()
    assert captured.out == ""
    written = [p for p in tmp_path.iterdir() if p.is_file()]
    assert written
    assert RESULT_TEXT in written[0].read_text(encoding="utf-8")


def test_live_result_not_echoed_when_both_file_sinks_are_set(
    tmp_path: Path, capsys
) -> None:
    groups = blank_parameter_groups()
    out_file = tmp_path / "single.txt"
    out_dir = tmp_path / "many"
    out_dir.mkdir()
    groups["op"].output_file_path_setting.set(out_file, ValueOrigin.CLI)
    groups["op"].output_directory_path_setting.set(out_dir, ValueOrigin.CLI)
    _run(groups, simulate=False, filename_schema="{CHUNK_FILE_NAME}.txt")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert RESULT_TEXT in out_file.read_text(encoding="utf-8")
    written = [p for p in out_dir.iterdir() if p.is_file()]
    assert written
    assert RESULT_TEXT in written[0].read_text(encoding="utf-8")


def test_simulate_board_stays_on_stdout_without_file_sink(capsys) -> None:
    groups = blank_parameter_groups()
    groups["aisp"].model_name_string_setting.set("mock-model", ValueOrigin.CLI)
    _run(groups, simulate=True)
    captured = capsys.readouterr()
    assert "| DRAGITER" in captured.out
    assert RESULT_TEXT not in captured.out


def test_simulate_board_not_echoed_when_output_file_is_set(
    tmp_path: Path, capsys
) -> None:
    groups = blank_parameter_groups()
    groups["aisp"].model_name_string_setting.set("mock-model", ValueOrigin.CLI)
    target = tmp_path / "sim.md"
    groups["op"].output_file_path_setting.set(target, ValueOrigin.CLI)
    _run(groups, simulate=True)
    captured = capsys.readouterr()
    assert captured.out == ""
    body = target.read_text(encoding="utf-8")
    assert "| DRAGITER" in body
    assert RESULT_TEXT not in body
