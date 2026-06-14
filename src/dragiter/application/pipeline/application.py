# from dragiter.processor import Application, ApplicationError
import logging

from dragiter.application.core.basic_checksum_generator import BasicChecksumGenerator
from dragiter.application.core.xdi import ApplicationManager

logger = logging.getLogger(__name__)


class Application(ApplicationManager):
    def __init__(self) -> None:
        super().__init__(BasicChecksumGenerator())


class ApplicationError(Exception):
    pass
