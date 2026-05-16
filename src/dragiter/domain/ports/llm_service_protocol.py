from typing import runtime_checkable

from dragiter.application.core.xdi import *


@runtime_checkable
class LLMServiceProtocol(Protocol):
    def ask(self, messages: List[Dict[str, str]] = []) -> str:
        ...

