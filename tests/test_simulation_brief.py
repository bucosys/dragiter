# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from __future__ import annotations

from support import blank_parameter_groups

from dragiter.application.pipeline.output_writer import OutputWriter
from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.context_validation_report import ContextValidationReport
from dragiter.domain.models.chat_sessions import ChatMessage, ChatSession, ChatSessions
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.settings import ValueOrigin
from dragiter.infrastructure.cli.simulation_brief import (
    COLUMN_WIDTHS,
    SimulationBrief,
    SimulationSessionBrief,
    format_simulation_panel_brief,
    format_simulation_session_brief,
    format_simulation_transcript,
    resolve_pack_budget,
)


def _sample() -> SimulationBrief:
    return SimulationBrief(
        model="qwen3:8b",
        sessions=6,
        chunks=3,
        valid_chunks=3,
        source_files=2,
        loop_items=2,
        total_chars=4812,
        sequential=False,
        pack_limit_chars=4000,
        pack_from="cli",
        peak_tokens=410,
        token_limit=8192,
        peak_session=2,
        window_ok=True,
        warning_count=0,
        small_chunks=0,
        oversize_chunks=0,
        output_dir="./outputs",
        output_file=None,
        result_count=6,
    )


def _expected_line_width() -> int:
    return 2 + sum(COLUMN_WIDTHS) + 3 * (len(COLUMN_WIDTHS) - 1) + 2


def test_panel_brief_pads_cells_to_fixed_width() -> None:
    text = format_simulation_panel_brief(_sample())
    lines = text.splitlines()
    width = _expected_line_width()
    assert all(len(line) == width for line in lines)
    assert set(lines[0]) <= {"|", " ", "-"}
    assert lines[1].startswith("| DRAGITER")
    assert lines[2] == lines[0]
    assert lines[-1] == lines[0]
    assert "qwen3:8b" in text
    assert "mode" in text
    assert "batched" in text
    assert "./outputs" in text
    assert "small / over" in text
    assert "pack from" in text
    assert "cli" in text
    assert "valid chunks" not in text


def test_file_board_is_valid_gfm() -> None:
    text = format_simulation_panel_brief(_sample(), frame=False)
    lines = text.splitlines()
    assert lines[0].startswith("| DRAGITER")
    assert set(lines[1]) <= {"|", " ", "-"}
    assert "DRAGITER" not in lines[1]
    assert lines[-1].startswith("| output")


def test_session_brief_names_chunk_and_loop() -> None:
    text = format_simulation_session_brief(
        SimulationSessionBrief(
            session_index=3,
            session_count=6,
            sequential=True,
            filename="notes.md",
            chunk_label="2 / 12",
            section="heading-03",
            loop_label="2 / 3",
            loop_line="Q2-limits",
            tokens=1929,
            chars=3992,
            pack_limit_chars=4000,
            pack_from="section",
            valid="yes",
            loop_items=3,
        )
    )
    lines = text.splitlines()
    assert all(len(line) == _expected_line_width() for line in lines)
    assert lines[0].startswith("| session")
    assert set(lines[1]) <= {"|", " ", "-"}
    assert lines[-1] != lines[1]
    assert "3 / 6" in text
    assert "sequential" in text
    assert "notes.md" in text
    assert "2 / 12" in text
    assert "heading-03" in text
    assert "yes" in text
    assert "loop index" in text
    assert "2 / 3" in text
    assert "loops" in text
    assert "1,929" in text
    assert "3,992" in text
    assert "4,000" in text
    assert "pack from" in text
    assert "section" in text
    assert "Q2-limits" not in text


def test_resolve_pack_budget_origins() -> None:
    assert resolve_pack_budget(True, 4000, [2000]) == (4000, "cli")
    assert resolve_pack_budget(True, 0, [4000]) == (None, "cli")
    assert resolve_pack_budget(False, None, [4000, 4000]) == (4000, "section")
    assert resolve_pack_budget(False, None, [4000, 2000]) == (None, "mixed")
    assert resolve_pack_budget(False, None, [None, 0]) == (None, "off")


def test_output_writer_marks_window_na_when_estimator_not_applicable(capsys) -> None:
    """
    The live pipeline always injects a ContextValidationReport. The
    not-applicable estimator result must render as n/a and -- / --, not
    yes and 0 / 0.
    """
    groups = blank_parameter_groups()
    groups["ep"].simulate_bool_setting.set(True, ValueOrigin.CLI)
    groups["aisp"].model_name_string_setting.set("mock-model", ValueOrigin.CLI)

    chunk = Chunk(
        num_id=1,
        filename="note.md",
        section_name="sec01",
        section_num_id=1,
        valid=True,
        content="hello",
    )
    session = ChatSession(
        input_chat_message_list=[ChatMessage(role="user", content="ask")],
        chunk=chunk,
    )
    result = ChatResult()
    result.output_chat_message.content = "mock-body"

    OutputWriter().run(
        ChatSessions([session]),
        ChatResults([result]),
        groups["op"],
        PromptTemplate("", "", "", "", 0.0, False, "", "\n\n"),
        groups["ep"],
        groups["aisp"],
        Material([chunk]),
        Loop(),
        ContextValidationReport(
            is_valid=None,
            total_tokens=0,
            max_tokens_limit=None,
            max_session_tokens=None,
        ),
    )

    captured = capsys.readouterr().out
    window_line = next(line for line in captured.splitlines() if "window" in line)
    peak_line = next(line for line in captured.splitlines() if "peak / limit" in line)
    assert "n/a" in window_line
    assert "yes" not in window_line
    assert "-- / --" in peak_line
    assert "0 / 0" not in peak_line


def test_output_writer_prints_padded_markdown_table(capsys) -> None:
    groups = blank_parameter_groups()
    groups["ep"].simulate_bool_setting.set(True, ValueOrigin.CLI)
    groups["aisp"].model_name_string_setting.set("mock-model", ValueOrigin.CLI)

    chunk = Chunk(
        num_id=1,
        filename="note.md",
        section_name="sec01",
        section_num_id=1,
        valid=True,
        content="hello",
    )
    session = ChatSession(
        input_chat_message_list=[ChatMessage(role="user", content="ask")],
        chunk=chunk,
        loop_item={"LOOP_CONTENT": "ask", "LOOP_NUM_ID": 1},
    )
    result = ChatResult()
    result.output_chat_message.content = '{"mock": true, "full_content": "secret prompt"}'

    OutputWriter().run(
        ChatSessions([session]),
        ChatResults([result]),
        groups["op"],
        PromptTemplate("", "", "", "", 0.0, False, "", "\n\n"),
        groups["ep"],
        groups["aisp"],
        Material([chunk]),
        Loop([{"LOOP_CONTENT": "ask", "LOOP_NUM_ID": 1}]),
    )

    captured = capsys.readouterr().out
    assert captured.lstrip().startswith("| -")
    assert "| DRAGITER" in captured
    assert "secret prompt" not in captured


def test_transcript_lists_payload_roles_then_assistant_briefing() -> None:
    text = format_simulation_transcript(
        [("system", "be brief"), ("user", "ask now")],
        "| DRAGITER         | simulate on      |",
    )
    lines = text.splitlines()
    assert lines[0] == "***"
    assert "| DRAGITER" in text
    assert "| R" in text
    assert "Content" in text
    assert any(line.startswith("| S ") and "be brief" in line for line in lines)
    assert any(line.startswith("| U ") and "ask now" in line for line in lines)
    assert not any(line.startswith("| A ") for line in lines)


def test_output_writer_writes_transcript_to_output_directory(tmp_path, capsys) -> None:
    groups = blank_parameter_groups()
    groups["ep"].simulate_bool_setting.set(True, ValueOrigin.CLI)
    groups["aisp"].model_name_string_setting.set("mock-model", ValueOrigin.CLI)
    groups["op"].output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("w", ValueOrigin.CLI)

    chunk = Chunk(1, "note.md", "sec01", 1, True, "hello")
    session = ChatSession(
        input_chat_message_list=[
            ChatMessage(role="system", content="persona"),
            ChatMessage(role="user", content="question"),
        ],
        chunk=chunk,
        loop_item={"LOOP_CONTENT": "question", "LOOP_NUM_ID": 1},
    )
    result = ChatResult()
    result.output_chat_message.content = '{"mock": true, "full_content": "secret prompt"}'

    OutputWriter().run(
        ChatSessions([session]),
        ChatResults([result]),
        groups["op"],
        PromptTemplate("", "", "", "", 0.0, True, "{CHUNK_FILE_NAME}.md", "\n\n"),
        groups["ep"],
        groups["aisp"],
        Material([chunk]),
        Loop([{"LOOP_CONTENT": "question", "LOOP_NUM_ID": 1}]),
    )

    written = list(tmp_path.glob("*.md"))
    assert written
    body = written[0].read_text(encoding="utf-8")
    assert body.lstrip().startswith("***")
    assert "| session" in body
    assert "note.md" in body
    assert "1 / 1" in body
    assert "\n\n| R" in body
    assert "| S " in body and "persona" in body
    assert "| U " in body and "question" in body
    assert "| A " not in body
    assert "secret prompt" not in body
    assert "| DRAGITER" not in body
    captured = capsys.readouterr()
    assert captured.out == ""


def test_output_writer_writes_transcript_to_output_file(tmp_path, capsys) -> None:
    groups = blank_parameter_groups()
    groups["ep"].simulate_bool_setting.set(True, ValueOrigin.CLI)
    groups["aisp"].model_name_string_setting.set("qwen3:8b", ValueOrigin.CLI)
    output_file = tmp_path / "result.md"
    groups["op"].output_file_path_setting.set(output_file, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("w", ValueOrigin.CLI)

    chunk = Chunk(1, "note.md", "sec01", 1, True, "hello")
    sessions = ChatSessions(
        [
            ChatSession(
                input_chat_message_list=[
                    ChatMessage(role="system", content="persona"),
                    ChatMessage(role="user", content="question one"),
                ],
                chunk=chunk,
                loop_item={"LOOP_CONTENT": "question one", "LOOP_NUM_ID": 1},
            ),
            ChatSession(
                input_chat_message_list=[
                    ChatMessage(role="system", content="persona"),
                    ChatMessage(role="user", content="question two"),
                ],
                chunk=chunk,
                loop_item={"LOOP_CONTENT": "question two", "LOOP_NUM_ID": 2},
            ),
        ]
    )
    results = ChatResults(
        [
            ChatResult(finish_reason="mock"),
            ChatResult(finish_reason="mock"),
        ]
    )
    results.chat_result_list[0].output_chat_message.content = '{"mock": true, "full_content": "secret 1"}'
    results.chat_result_list[1].output_chat_message.content = '{"mock": true, "full_content": "secret 2"}'

    OutputWriter().run(
        sessions,
        results,
        groups["op"],
        PromptTemplate("", "", "", "", 0.0, False, "", "\n---\n"),
        groups["ep"],
        groups["aisp"],
        Material([chunk]),
        Loop(
            [
                {"LOOP_CONTENT": "question one", "LOOP_NUM_ID": 1},
                {"LOOP_CONTENT": "question two", "LOOP_NUM_ID": 2},
            ]
        ),
    )

    body = output_file.read_text(encoding="utf-8")
    assert '"mock"' not in body
    assert body.lstrip().startswith("***")
    assert "| DRAGITER" in body
    assert body.count("\n| session ") == 2
    assert "question one" in body
    assert "question two" in body
    assert body.count("\n\n| R") >= 2
    assert "| A " not in body
    captured = capsys.readouterr()
    assert captured.out == ""
