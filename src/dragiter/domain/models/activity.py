import logging

from attic.configuration import Configuration

logger = logging.getLogger(__name__)


class Activity:
    def __init__(self, config: Configuration) -> None:
        """Initialise the configuration object and load settings."""
        self.config = config

    def append(self, what: str) -> None:
        """append something to activity logs"""
