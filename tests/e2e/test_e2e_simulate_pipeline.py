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

import json
import os
from pathlib import Path
import sys

from dragiter.application.config.configuration_loader import ConfigurationLoader
from dragiter.application.config.configuration_validator import ConfigurationValidator
from dragiter.application.core.xdi import ApplicationManager
from dragiter.application.pipeline.chat_manager import ChatManager
from dragiter.application.pipeline.context_window_estimator import ContextWindowEstimator
from dragiter.application.pipeline.loop_builder import LoopBuilder
from dragiter.application.pipeline.material_tokenizer import MaterialTokenizer
from dragiter.application.pipeline.message_builder import MessageBuilder
from dragiter.application.pipeline.output_writer import OutputWriter
from dragiter.application.pipeline.prompt_creator import PromptCreator
from dragiter.application.pipeline.resource_collector import ResourceCollector
from dragiter.domain.services.chat_sessions_validator import ChatSessionsValidator
from dragiter.infrastructure.checksum.basic_checksum_generator import BasicChecksumGenerator
from dragiter.infrastructure.cli.markdown_result_board import MarkdownResultBoard
from dragiter.infrastructure.cli.null_session_board import NullSessionBoard
from dragiter.infrastructure.cli.stderr_session_board import StderrSessionBoard
from dragiter.infrastructure.file.simple_file_checker import SimpleFileChecker
from dragiter.infrastructure.file.simple_text_file_reader import SimpleTextFileReader
from dragiter.infrastructure.io.workspace_service import (
    DIR_STAGING_PREFIX,
    FILE_STAGING_PREFIX,
    WorkspaceCommitService,
    WorkspaceLayout,
    WorkspacePersistenceService,
    user_temp_directory,
)
from dragiter.infrastructure.llm.mockai_service import MockAIService
from dragiter.infrastructure.llm.simple_payload_estimator import SimplePayloadEstimator
from dragiter.infrastructure.logging.file_activity_logger import FileActivityLogger


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

        layout = WorkspaceLayout(pid=os.getpid(), user_temp=user_temp_directory(os.environ))
        app = ApplicationManager(BasicChecksumGenerator(), FileActivityLogger())
        app.register_worker(ConfigurationLoader())
        app.register_worker(ConfigurationValidator())
        app.register_worker(ResourceCollector(SimpleFileChecker()))
        app.register_worker(MaterialTokenizer(SimpleTextFileReader()))
        app.register_worker(LoopBuilder())
        app.register_worker(PromptCreator())
        app.register(MessageBuilder(), ChatSessionsValidator())
        app.register_worker(ContextWindowEstimator(SimplePayloadEstimator()))
        app.register_worker(
            ChatManager(
                _ForbiddenLiveService(),
                MockAIService(),
                StderrSessionBoard(sys.stderr, interactive=False),
                NullSessionBoard(),
                WorkspacePersistenceService(layout),
                MarkdownResultBoard(),
            )
        )
        app.register_worker(OutputWriter(WorkspaceCommitService(layout, sys.stdout)))
        app.run()
        return 0
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return int(code) if not isinstance(code, int) else code
    finally:
        sys.argv = saved_argv


class _ForbiddenLiveService:
    """Live slot in e2e runs: simulate mode must never reach it."""

    def process_query(self, aisp, lp, chat_session, progress=None):
        raise AssertionError("e2e simulate run reached the live LLM service")


def test_simulate_pipeline_writes_mock_output(tiny_example_dir: Path) -> None:
    """
    Full simulate run against the self-contained tiny fixtures.

    Expectations:
      * exit code 0
      * at least one output file under -O
      * every output file is a role/content Markdown transcript

    SIMU-01 (the live service is `_ForbiddenLiveService`, never actually
    called), SIMU-02 (no assistant/reply row in the output).
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

    SIMU-04.
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
