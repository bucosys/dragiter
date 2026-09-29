# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import logging
import os
import sys

from dragiter.application.config.configuration_loader import ConfigurationLoader
from dragiter.application.config.configuration_validator import ConfigurationValidator
from dragiter.application.config.logging_configuration import (
    LoggingConfiguration,
    LoggingConfigurator,
)
from dragiter.application.core.xdi import ApplicationManager
from dragiter.application.pipeline.chat_manager import ChatManager
from dragiter.application.pipeline.context_window_estimator import (
    ContextWindowEstimator,
)
from dragiter.application.pipeline.loop_builder import LoopBuilder
from dragiter.application.pipeline.material_tokenizer import MaterialTokenizer
from dragiter.application.pipeline.message_builder import MessageBuilder
from dragiter.application.pipeline.output_writer import OutputWriter
from dragiter.application.pipeline.prompt_creator import PromptCreator
from dragiter.application.pipeline.resource_collector import ResourceCollector
from dragiter.domain.services.chat_sessions_validator import ChatSessionsValidator
from dragiter.infrastructure.checksum.basic_checksum_generator import BasicChecksumGenerator
from dragiter.infrastructure.cli.info_presenter import InfoPresenter
from dragiter.infrastructure.cli.markdown_result_board import MarkdownResultBoard
from dragiter.infrastructure.cli.null_session_board import NullSessionBoard
from dragiter.infrastructure.cli.resource_exporter import ResourceExporter
from dragiter.infrastructure.cli.stderr_session_board import StderrSessionBoard
from dragiter.infrastructure.file.simple_file_checker import SimpleFileChecker
from dragiter.infrastructure.file.simple_text_file_reader import SimpleTextFileReader
from dragiter.infrastructure.io.workspace_service import (
    NewestWorkspaceSeeder,
    NullWorkspaceSeeder,
    WorkspaceCommitService,
    WorkspaceLayout,
    WorkspacePersistenceService,
    user_temp_directory,
)
from dragiter.infrastructure.llm.mockai_service import MockAIService
from dragiter.infrastructure.llm.openai_service_ext import OpenAIServiceExt
from dragiter.infrastructure.llm.simple_payload_estimator import SimplePayloadEstimator
from dragiter.infrastructure.logging.file_activity_logger import FileActivityLogger


def gen_docs():
    """Triggered by the command 'dragiter-gen-docs'"""
    ResourceExporter.export("docs")


def gen_examples():
    """Triggered by the command 'dragiter-gen-examples'"""
    ResourceExporter.export("examples")


def main():
    ## PRE SELECTOR
    # S1: No params ? show usage

    if len(sys.argv) == 1:
        InfoPresenter.print_banner()
        return InfoPresenter.show_usage()

    # -------------------------------------------
    # S2: help-switches ? show usage
    if any(arg.lower() in ("--info", "-info", "/info") for arg in sys.argv):
        return InfoPresenter.show_help()

    ## PRE TASK
    logconf: LoggingConfiguration = LoggingConfigurator.parse_and_configure()
    logger = logging.getLogger(__name__)

    ## TASK THE CHAIN
    try:
        app = ApplicationManager(BasicChecksumGenerator(), FileActivityLogger())

        # One layout for both ends of the staging pipeline: ChatManager persists
        # into it, OutputWriter commits out of it (STAG).
        workspace_layout = WorkspaceLayout(
            pid=os.getpid(), user_temp=user_temp_directory(os.environ)
        )

        app.register_worker(ConfigurationLoader())
        app.register_worker(ConfigurationValidator())
        app.register_worker(ResourceCollector(SimpleFileChecker()))  # -> Resources
        app.register_worker(MaterialTokenizer(SimpleTextFileReader()))  # -> Material
        app.register_worker(LoopBuilder())  # -> Loop
        app.register_worker(PromptCreator())  # -> PromptTemplate
        app.register(MessageBuilder(), ChatSessionsValidator())  # -> ChatSessions
        app.register_worker(ContextWindowEstimator(SimplePayloadEstimator()))  # -> None
        app.register_worker(
            ChatManager(
                OpenAIServiceExt(),
                MockAIService(),
                StderrSessionBoard(sys.stderr, interactive=sys.stderr.isatty()),
                NullSessionBoard(),
                WorkspacePersistenceService(
                    workspace_layout, NullWorkspaceSeeder(), NewestWorkspaceSeeder()
                ),
                MarkdownResultBoard(),
            )
        )  # -> ChatResults
        app.register_worker(
            OutputWriter(WorkspaceCommitService(workspace_layout, sys.stdout))
        )  # -> ApplicationResult
        app.run()

        return 0

    except KeyboardInterrupt:
        # Using stderr for the interrupt message is good practice
        print("\n[!] Process interrupted by user.", file=sys.stderr)
        return 130
    except Exception as e:
        # Log the full error message to stderr

        logger.error(f"A critical error occurred: {e}", exc_info=logconf.debug)
        return 1


if __name__ == "__main__":
    # Pass the integer return value from main() directly to the OS
    sys.exit(main())
