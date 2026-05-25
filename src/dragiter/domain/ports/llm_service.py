from typing import runtime_checkable, Protocol, List, Dict
from dragiter.domain.models.ai_service_parameters import AIServiceParameters


@runtime_checkable
class LLMService(Protocol):
    def process_query(self, aisp: AIServiceParameters, messages: List[Dict[str, str]] = []) -> str:
        ...

