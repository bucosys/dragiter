from typing import List, Dict

from dragiter.domain.ports.llm_service import LLMService


class LLMServiceAdapter(LLMService):

    def __init__(self, llm_service_protocol: LLMService) -> None:
        self.llm_service_protocol = llm_service_protocol


    """one interface for all services"""
    def process_query(self, messages: List[Dict[str, str]] = []) -> str:
        return self.llm_service_protocol.process_query(messages)