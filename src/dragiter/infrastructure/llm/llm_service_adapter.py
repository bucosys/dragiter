from typing import List, Dict

from dragiter.domain.ports.llm_service_protocol import LLMServiceProtocol


class LLMServiceAdapter(LLMServiceProtocol):

    def __init__(self, llm_service_protocol: LLMServiceProtocol) -> None:
        self.llm_service_protocol = llm_service_protocol


    """one interface for all services"""
    def ask(self, messages: List[Dict[str, str]] = []) -> str:
        return self.llm_service_protocol.ask(messages)