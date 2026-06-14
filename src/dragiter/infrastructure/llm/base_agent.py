import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# --- 1. The Interface (Abstract Base Class) ---
class BaseAgent(ABC):
    """
    The interface defines what every agent must be able to do.
    This keeps the rest of the code independent of the specific API.
    """

    @abstractmethod
    def ask(self, instruction: str, task: str) -> str:
        pass
