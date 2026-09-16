# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from __future__ import annotations

import os
from pathlib import Path

import pytest
from support import blank_parameter_groups

from dragiter.application.pipeline.chat_manager import ChatManager, ChatManagerError
from dragiter.application.pipeline.output_writer import OutputWriter
from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.chat_sessions import ChatMessage, ChatSession, ChatSessions
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.context_validation_report import ContextValidationReport
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.resources import Resources
from dragiter.domain.models.settings import ValueOrigin
from dragiter.infrastructure.cli.markdown_result_board import MarkdownResultBoard
from dragiter.infrastructure.io.workspace_service import (
    DIR_STAGING_PREFIX,
    EXCLUSIVE_RUNTIME_NOTICE,
    WorkspacePersistenceService,
    cleanup_run_workspaces,
    commit_assembled_output,
    dir_workspace_path,
)


def _prompt(schema: str = "{CHUNK_FILE_NAME}.txt", delimiter: str = "\n---\n") -> PromptTemplate:
    return PromptTemplate("", "", "", "", 0.0, False, schema, delimiter)


def _session(name: str, loop_id: int = 1) -> ChatSession:
    chunk = Chunk(1, name, "sec01", 1, True, "hello")
    return ChatSession(
        input_chat_message_list=[ChatMessage(role="user", content="ask")],
        chunk=chunk,
        loop_item={"LOOP_CONTENT": "ask", "LOOP_NUM_ID": loop_id},
    )


def _result(text: str, simulate: bool = False) -> ChatResult:
    result = ChatResult(finish_reason="mock" if simulate else "stop")
    result.output_chat_message.content = text
    return result


def _writer_run(groups, sessions, results, prompt) -> None:
    chunk = sessions.session_list[0].chunk
    OutputWriter(MarkdownResultBoard()).run(
        sessions,
        results,
        groups["op"],
        prompt,
        groups["ep"],
        groups["aisp"],
        Material([chunk] if chunk is not None else []),
        Loop([session.loop_item or {} for session in sessions.session_list]),
    )


def test_workspace_path_is_one_directory(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    groups["op"].output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    path = dir_workspace_path(groups["op"], pid=4242)
    assert path == tmp_path / f"{DIR_STAGING_PREFIX}4242"


def test_exclusive_file_conflict_before_chat(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    groups["op"].output_file_path_setting.set(target, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("x", ValueOrigin.CLI)
    sessions = ChatSessions([_session("a.md")])
    with pytest.raises(ChatManagerError, match="refusing to start"):
        ChatManager(_NeverCalled()).run(
            groups["aisp"],
            groups["lp"],
            groups["ep"],
            sessions,
            groups["op"],
            Material([]),
            Loop(),
            ContextValidationReport(is_valid=True, total_tokens=0, max_tokens_limit=0),
            Resources(),
            _prompt(),
        )
    assert not dir_workspace_path(groups["op"]).exists()


class _NeverCalled:
    def process_query(self, aisp, lp, session, progress=None):
        raise AssertionError("completion must not run after an exclusive conflict")


def test_exclusive_duplicate_planned_names_before_chat(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    groups["op"].output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("x", ValueOrigin.CLI)
    sessions = ChatSessions([_session("same.md", 1), _session("same.md", 2)])
    with pytest.raises(ChatManagerError, match="refusing to start"):
        ChatManager(_NeverCalled()).run(
            groups["aisp"],
            groups["lp"],
            groups["ep"],
            sessions,
            groups["op"],
            Material([]),
            Loop(),
            ContextValidationReport(is_valid=True, total_tokens=0, max_tokens_limit=0),
            Resources(),
            _prompt("{CHUNK_FILE_NAME}.txt"),
        )
    assert not dir_workspace_path(groups["op"]).exists()


def test_timestamp_schema_skips_early_exclusive_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    groups = blank_parameter_groups()
    groups["op"].output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("x", ValueOrigin.CLI)
    prompt = _prompt("out_{TIMESTAMP}.txt")
    service = WorkspacePersistenceService(op=groups["op"], prompt=prompt)
    service.check_exclusive([_session("a.md")])
    err = capsys.readouterr().err
    assert EXCLUSIVE_RUNTIME_NOTICE in err
    service.prepare()
    assert service.dir_workspace.is_dir()


def test_commit_append_inserts_delimiter(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    target.write_text("old", encoding="utf-8")
    commit_assembled_output(target, "a", "new", "\n---\n")
    assert target.read_text(encoding="utf-8").strip() == "old\n---\nnew"


def test_commit_empty_body_does_not_touch_target(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    target.write_text("old", encoding="utf-8")
    commit_assembled_output(target, "a", "  \n", "\n---\n")
    assert target.read_text(encoding="utf-8") == "old"
    assert not (tmp_path / "missing.md").exists()
    commit_assembled_output(tmp_path / "missing.md", "a", "", "\n---\n")
    assert not (tmp_path / "missing.md").exists()


def test_output_writer_cleans_workspaces_after_success(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    out_file = tmp_path / "one.txt"
    out_dir = tmp_path / "many"
    out_dir.mkdir()
    groups["op"].output_file_path_setting.set(out_file, ValueOrigin.CLI)
    groups["op"].output_directory_path_setting.set(out_dir, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("w", ValueOrigin.CLI)
    prompt = _prompt("{CHUNK_FILE_NAME}.txt", "\n")
    service = WorkspacePersistenceService(groups["op"], prompt)
    service.prepare()
    session = _session("note.md")
    result = _result("payload")
    service.persist(1, session, result)
    assert service.dir_workspace.is_dir()
    assert list(service.dir_workspace.iterdir())
    _writer_run(
        groups,
        ChatSessions([session]),
        ChatResults([result]),
        prompt,
    )
    assert out_file.read_text(encoding="utf-8").strip() == "payload"
    written = [p for p in out_dir.iterdir() if p.is_file()]
    assert written and written[0].read_text(encoding="utf-8").strip() == "payload"
    assert not dir_workspace_path(groups["op"]).exists()
    assert not list(tmp_path.glob(".dragiter-partial"))
    assert not list(out_dir.glob(".dragiter-partial"))


def test_live_commit_prefers_workspace_over_memory(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    out_file = tmp_path / "one.txt"
    out_dir = tmp_path / "many"
    out_dir.mkdir()
    groups["op"].output_file_path_setting.set(out_file, ValueOrigin.CLI)
    groups["op"].output_directory_path_setting.set(out_dir, ValueOrigin.CLI)
    groups["op"].output_mode_string_setting.set("w", ValueOrigin.CLI)
    prompt = _prompt("{CHUNK_FILE_NAME}.txt", "\n")
    service = WorkspacePersistenceService(groups["op"], prompt)
    service.prepare()
    session = _session("note.md")
    disk = _result("from-workspace")
    ram = _result("from-memory")
    service.persist(1, session, disk)
    _writer_run(groups, ChatSessions([session]), ChatResults([ram]), prompt)
    assert "from-workspace" in out_file.read_text(encoding="utf-8")
    assert "from-memory" not in out_file.read_text(encoding="utf-8")
    written = [p for p in out_dir.iterdir() if p.is_file()]
    assert written
    body = written[0].read_text(encoding="utf-8")
    assert "from-workspace" in body
    assert "from-memory" not in body


def test_persist_writes_one_timestamp_file_per_session(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    groups["op"].output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    prompt = _prompt("{CHUNK_SECTION_NAME}.txt")
    service = WorkspacePersistenceService(groups["op"], prompt)
    service.prepare()
    service.persist(1, _session("a.md", 1), _result("first"))
    service.persist(2, _session("b.md", 2), _result(""))
    stored = sorted(p for p in service.dir_workspace.iterdir() if p.is_file())
    assert len(stored) == 2
    assert stored[0].read_text(encoding="utf-8") == "first"
    assert stored[1].read_text(encoding="utf-8") == ""


def test_cleanup_ignores_foreign_pid(tmp_path: Path) -> None:
    groups = blank_parameter_groups()
    groups["op"].output_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    foreign = tmp_path / f"{DIR_STAGING_PREFIX}1"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("x", encoding="utf-8")
    cleanup_run_workspaces(groups["op"], pid=os.getpid())
    assert foreign.is_dir()
