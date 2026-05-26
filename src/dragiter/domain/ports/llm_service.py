from typing import runtime_checkable, Protocol, List, Dict
from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.chat_message import ExtendedMessages, ChatResult


@runtime_checkable
class LLMService(Protocol):
    def process_query(self, aisp: AIServiceParameters, extended_messages: ExtendedMessages ) -> ChatResult :
        ...

class LLMServiceError(Exception):
    pass