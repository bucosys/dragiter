import logging
from datetime import datetime
from typing import List, Dict

from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.chat_result import ChatResult
from dragiter.domain.ports.llm_service import LLMService

logger = logging.getLogger(__name__)


class MockAIService(LLMService):
    def __init__(self, ai_service_parameters: AIServiceParameters):
        self.ai_service_parameters = ai_service_parameters

        logger.debug(f"🔧 (Mock AI SDK) values initialized. Model: {self.model_name}")

    def process_query(self, aisp: AIServiceParameters, messages: List[Dict[str, str]] = []) -> ChatResult:
        """
        Simulates an LLM response by echoing the last user message.
        Useful for verifying that prompts and materials were correctly merged.
        """

        logger.debug(f"🔧 (Mock AI SDK) values initialized. Model: {aisp.model_name_string.value}")

        # Fallback if messages list is empty
        if not messages:
            logger.warning("Mock AI received an empty message list.")
            return f"MOCK_AI: No input received at {datetime.now()}"

        # Get the last message (usually the user prompt with the injected material)
        last_msg = messages[-1]
        role = last_msg.get("role", "unknown")
        content = last_msg.get("content", "")
        chat_result = ChatResult(role="assistent")

        chat_result.started_at = datetime.now()

        # Create a detailed response for debugging
        mock_response = (
            f"[START MOCK AI RESPONSE ({aisp.model_name_string.value})]\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Detected Role: {role}\n"
            f"Content Preview: {content[:50]}...\n"
            f"--- FULL CONTENT ECHO ---\n"
            f"{content}\n"
            f"[END OF MOCK]"
        )

        logger.debug(f"Mock AI generated echo for role '{role}'")
        chat_result.finis_response = "MOCK_AI"
        chat_result.content = mock_response
        chat_result.ended_at = datetime.now()
        chat_result.duration_ms = (chat_result.ended_at - chat_result.started_at).total_seconds()

        return chat_result