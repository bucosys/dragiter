import logging

logger = logging.getLogger(__name__)


class LLMServiceResult:
    def __init__(self, results: list[str] = []) -> None:
        """Initialise the configuration object and load settings."""
        self._results = results

    # Properties for clean access
    @property
    def results(self):
        return self._results

    def __repr__(self):
        # dedicated for logger
        return f"ProcessorResult (results length ='{len(self._results)}')"
