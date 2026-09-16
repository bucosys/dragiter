# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
End-to-end simulation-mode pipeline test.

Runs the full worker chain (config → resources → chunks → loop → mock LLM →
output) without any network access and without importing the live OpenAI
adapters. This is the highest-ROI integration check: unit tests can be green
while the wiring between pipeline workers is broken.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
import sys
from typing import Any

from dragiter.application.config.configuration_loader import ConfigurationLoader
from dragiter.application.config.configuration_validator import ConfigurationValidator
from dragiter.application.core.file_activity_logger import FileActivityLogger
from dragiter.application.pipeline.application import Application
from dragiter.application.pipeline.chat_manager import ChatManager
from dragiter.application.pipeline.context_window_estimator import ContextWindowEstimator
from dragiter.application.pipeline.loop_builder import LoopBuilder
from dragiter.application.pipeline.material_tokenizer import MaterialTokenizer
from dragiter.application.pipeline.message_builder import MessageBuilder
from dragiter.application.pipeline.output_writer import OutputWriter
from dragiter.application.pipeline.prompt_creator import PromptCreator
from dragiter.application.pipeline.resource_collector import ResourceCollector
from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import AIServiceParameters
from dragiter.domain.services.chat_sessions_validator import ChatSessionsValidator
from dragiter.infrastructure.cli.markdown_result_board import MarkdownResultBoard
from dragiter.infrastructure.file.simple_file_checker import SimpleFileChecker
from dragiter.infrastructure.file.simple_text_file_reader import SimpleTextFileReader
from dragiter.infrastructure.io.workspace_service import (
    DIR_STAGING_PREFIX,
    FILE_STAGING_PREFIX,
)
from dragiter.infrastructure.llm.mockai_service import MockAIService
from dragiter.infrastructure.llm.simple_payload_estimator import SimplePayloadEstimator

_ORIGINAL_MOCK_PROCESS_QUERY = MockAIService.process_query


def _mock_process_query_arity() -> int:
    """Number of parameters after ``self`` on the unpatched MockAIService."""
    names = [
        parameter.name
        for parameter in inspect.signature(_ORIGINAL_MOCK_PROCESS_QUERY).parameters.values()
        if parameter.name != "self"
    ]
    return len(names)


def _compatible_process_query(
    self: MockAIService,
    aisp: AIServiceParameters,
    lp_or_session: Any,
    chat_session: ChatSession | None = None,
    progress: Any = None,
) -> ChatResult:
    """
    Accept both the Protocol signature (aisp, lp, session) and the
    historical MockAIService signature (aisp, session).

    ChatManager always constructs a fresh MockAIService in simulate mode,
    so this adapter is installed on the class rather than on one instance.
    """
    session = chat_session if isinstance(chat_session, ChatSession) else lp_or_session
    if not isinstance(session, ChatSession):
        raise TypeError(f"Expected ChatSession, got {type(session).__name__}")

    if _mock_process_query_arity() >= 3:
        logging_parameters = None if isinstance(lp_or_session, ChatSession) else lp_or_session
        return _ORIGINAL_MOCK_PROCESS_QUERY(self, aisp, logging_parameters, session)
    return _ORIGINAL_MOCK_PROCESS_QUERY(self, aisp, session)


def _run_simulate_pipeline(flags: list[str]) -> int:
    """
    Execute the application worker chain in-process.

    Avoids ``python -m dragiter.cli``, which imports the live OpenAI adapters
    (``openai`` / ``httpx2``) even in ``-s`` mode and therefore fails in
    environments that only exercise simulation.
    """
    saved_argv = sys.argv
    try:
        sys.argv = ["dragiter", *flags]
        # Do not preload stdin. A template without {STDIN} and without -t
        # must not block on an inherited, still-open standard input.
        MockAIService.process_query = _compatible_process_query  # type: ignore[method-assign]

        app = Application()
        app.register_activity_logger(FileActivityLogger())
        app.register_worker(ConfigurationLoader())
        app.register_worker(ConfigurationValidator())
        app.register_worker(ResourceCollector(SimpleFileChecker()))
        app.register_worker(MaterialTokenizer(SimpleTextFileReader()))
        app.register_worker(LoopBuilder())
        app.register_worker(PromptCreator())
        app.register(MessageBuilder(), ChatSessionsValidator())
        app.register_worker(ContextWindowEstimator(SimplePayloadEstimator()))
        app.register_worker(ChatManager(MockAIService(SimplePayloadEstimator())))
        app.register_worker(OutputWriter(MarkdownResultBoard()))
        app.run()
        return 0
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return int(code) if not isinstance(code, int) else code
    finally:
        MockAIService.process_query = _ORIGINAL_MOCK_PROCESS_QUERY  # type: ignore[method-assign]
        sys.argv = saved_argv


def test_simulate_pipeline_writes_mock_output(tiny_example_dir: Path) -> None:
    """
    Full simulate run against the self-contained tiny fixtures.

    Expectations:
      * exit code 0
      * at least one output file under -O
      * every output file is a role/content Markdown transcript
    """
    output_dir = tiny_example_dir / "outputs" / "simulate_e2e"
    output_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-s",
        "-v",
        "-b",
        str(tiny_example_dir),
        "-p",
        str(tiny_example_dir / "01_tiny_prompt.toml"),
        "-r",
        str(tiny_example_dir / "01_tiny_resource.toml"),
        "-l",
        str(tiny_example_dir / "01_tiny_loop.txt"),
        "-O",
        str(output_dir),
        "-m",
        "w",
    ]

    returncode = _run_simulate_pipeline(flags)
    assert returncode == 0, f"Simulate pipeline failed (exit {returncode})."

    created = [
        p
        for p in output_dir.rglob("*")
        if p.is_file()
        and DIR_STAGING_PREFIX not in p.name
        and FILE_STAGING_PREFIX not in p.name
        and not any(
            part.startswith(DIR_STAGING_PREFIX) for part in p.parts
        )
    ]
    assert created, f"No output files written to {output_dir}"

    for path in created:
        text = path.read_text(encoding="utf-8")
        assert text.lstrip().startswith("***"), (
            f"Output {path.name} does not start with a ruled Markdown board:\n{text[:400]}"
        )
        assert "| session" in text
        assert "\n\n| R" in text
        assert "| A " not in text and "| A|" not in text


def test_simulate_pipeline_with_activity_log(tiny_example_dir: Path) -> None:
    """
    Same pipeline plus activity JSONL — verifies the audit path is wired.
    """
    output_dir = tiny_example_dir / "outputs" / "simulate_e2e_activity"
    output_dir.mkdir(parents=True, exist_ok=True)
    activity_file = tiny_example_dir / "activity_simulate.jsonl"

    flags = [
        "-s",
        "-b",
        str(tiny_example_dir),
        "-p",
        str(tiny_example_dir / "01_tiny_prompt.toml"),
        "-r",
        str(tiny_example_dir / "01_tiny_resource.toml"),
        "-l",
        str(tiny_example_dir / "01_tiny_loop.txt"),
        "-O",
        str(output_dir),
        "-m",
        "w",
        "-a",
        str(activity_file),
    ]

    returncode = _run_simulate_pipeline(flags)
    assert returncode == 0, (
        f"Simulate pipeline with activity log failed (exit {returncode})."
    )

    assert activity_file.is_file(), "Activity file was not created"
    lines = [
        line
        for line in activity_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 2, "Activity log should contain several records"

    for line in lines:
        json.loads(line)
