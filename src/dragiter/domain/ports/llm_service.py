from typing import runtime_checkable, Protocol

from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession


@runtime_checkable
class LLMService(Protocol):
    def process_query(self, aisp: AIServiceParameters, chat_session: ChatSession) -> ChatResult:
        ...


class LLMServiceError(Exception):
    pass
