from typing import runtime_checkable, Protocol, List, Dict
from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.chat_sessions import ChatMessage, ChatSession


@runtime_checkable
class LLMService(Protocol):
    def process_query(self, aisp: AIServiceParameters, chat_session: ChatSession ) -> ChatSession :
        ...

class LLMServiceError(Exception):
    pass