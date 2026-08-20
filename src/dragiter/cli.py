# =============================================================================
# dragiter - Deterministic Context Iterator
# Copyright (c) 2026 Michael Buchold <michael.buchold@dragiter.app>
#
# This file is part of dragiter.
#
# dragiter is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dragiter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with dragiter. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing (closed-source use, SaaS, etc.), please contact:
# Michael Buchold <michael.buchold@dragiter.app>
# =============================================================================

import logging
import sys

from dragiter.application.config.configuration_loader import ConfigurationLoader
from dragiter.application.config.configuration_validator import ConfigurationValidator
from dragiter.application.config.logging_configuration import (
    LoggingConfiguration,
    LoggingConfigurator,
)
from dragiter.application.core.file_activity_logger import FileActivityLogger
from dragiter.application.pipeline.application import Application
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
from dragiter.infrastructure.cli.info_presenter import InfoPresenter
from dragiter.infrastructure.cli.resource_exporter import ResourceExporter
from dragiter.infrastructure.file.simple_file_checker import SimpleFileChecker
from dragiter.infrastructure.file.simple_text_file_reader import SimpleTextFileReader
from dragiter.infrastructure.llm.openai_service import OpenAIService
from dragiter.infrastructure.llm.simple_payload_estimator import SimplePayloadEstimator


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
        app = Application()
        app.register_activity_logger(FileActivityLogger())
        app.register_worker(ConfigurationLoader())
        app.register_worker(ConfigurationValidator())
        app.register_worker(ResourceCollector(SimpleFileChecker()))  # -> Resources
        app.register_worker(MaterialTokenizer(SimpleTextFileReader()))  # -> Material
        app.register_worker(LoopBuilder())  # -> Loop
        app.register_worker(PromptCreator())  # -> PromptTemplate
        app.register(MessageBuilder(), ChatSessionsValidator())  # -> ChatSessions
        app.register_worker(ContextWindowEstimator(SimplePayloadEstimator()))  # -> None
        app.register_worker(ChatManager(OpenAIService()))  # -> ChatResults
        app.register_worker(OutputWriter())  # -> ApplicationResult
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
