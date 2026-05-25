from typing import Protocol

from dragiter.domain.models.chat_message import ChatMessages

class PayloadEstimator(Protocol):
    """
    Structural interface for payload token estimation.
    """
    def estimate(self, chat_messages: ChatMessages, chars_per_token: float) -> int:
        ...



class PayloadEstimatorError(Exception):
    pass
