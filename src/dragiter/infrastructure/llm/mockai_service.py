import logging
from datetime import datetime
from typing import List, Dict

from dragiter.domain.ports.llm_service_protocol import LLMServiceProtocol

logger = logging.getLogger(__name__)


class MockAIService(LLMServiceProtocol):
    def __init__(self, api_key: str, base_url: str, model_name: str, temperature: float = 0.0):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = temperature

        logger.debug(f"🔧 (Mock AI SDK) values initialized. Model: {self.model_name}")

    def ask(self, messages: List[Dict[str, str]] = []) -> str:
        """
        Simulates an LLM response by echoing the last user message.
        Useful for verifying that prompts and materials were correctly merged.
        """
        # Fallback if messages list is empty
        if not messages:
            logger.warning("Mock AI received an empty message list.")
            return f"MOCK_AI: No input received at {datetime.now()}"

        # Get the last message (usually the user prompt with the injected material)
        last_msg = messages[-1]
        role = last_msg.get("role", "unknown")
        content = last_msg.get("content", "")

        # Create a detailed response for debugging
        mock_response = (
            f"[START MOCK AI RESPONSE ({self.model_name})]\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Detected Role: {role}\n"
            f"Content Preview: {content[:50]}...\n"
            f"--- FULL CONTENT ECHO ---\n"
            f"{content}\n"
            f"[END OF MOCK]"
        )

        logger.debug(f"Mock AI generated echo for role '{role}'")
        return mock_response