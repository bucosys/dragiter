import logging
import os
import sys
import shutil
import importlib.resources
from pathlib import Path

from dragiter.application.config.configuration_loader import ConfigurationLoader
from dragiter.application.config.configuration_validator import ConfigurationValidator
from dragiter.application.pipeline.application import Application
from dragiter.application.pipeline.chat_manager import ChatManager
from dragiter.application.pipeline.context_window_validator import ContextWindowValidator
from dragiter.application.pipeline.llm_service_factory import LLMServiceFactory
from dragiter.application.pipeline.loop_builder import LoopBuilder
from dragiter.application.pipeline.material_tokenizer import MaterialTokenizer
from dragiter.application.pipeline.resource_collector import ResourceCollector
from dragiter.application.pipeline.message_builder import MessageBuilder
from dragiter.application.pipeline.output_writer import OutputWriter
from dragiter.application.pipeline.prompt_creator import PromptCreator
from dragiter.infrastructure.file.simple_file_checker import SimpleFileChecker
from dragiter.infrastructure.file.simple_text_file_reader import SimpleTextFileReader
from dragiter.infrastructure.cli.resource_exporter import ResourceExporter
from dragiter.infrastructure.cli.info_presenter import InfoPresenter
from dragiter.application.config.logging_configuration import LoggingConfiguration, LoggingConfigurator
from dragiter.infrastructure.llm.mockai_service import MockAIService
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
        app.register(ConfigurationLoader())
        app.register(ConfigurationValidator())
        app.register(ResourceCollector(SimpleFileChecker()))
        app.register(MaterialTokenizer(SimpleTextFileReader()))
        app.register(LoopBuilder())
        app.register(PromptCreator())
        app.register(MessageBuilder())
        app.register(ContextWindowValidator(SimplePayloadEstimator()))
        app.register(ChatManager(OpenAIService()))
        app.register(OutputWriter())
        app.run()

        return 0



    except (KeyboardInterrupt) as e:
        # Using stderr for the interrupt message is good practice
        print("\n[!] Process interrupted by user.", file=sys.stderr)
        return 130
    except Exception as e:
        # Log the full error message to stderr

        logger.error(f"A critical error occurred: {e}", exc_info=logconf.verbose)
        return 1

if __name__ == "__main__":
    # Pass the integer return value from main() directly to the OS
    sys.exit(main())