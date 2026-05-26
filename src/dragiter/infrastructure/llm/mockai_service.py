import logging
from datetime import datetime
from typing import List, Dict

from dragiter.domain.models.ai_service_parameters import AIServiceParameters

from dragiter.domain.models.chat_message import ExtendedMessages, ChatMessage, ChatResult, ExtendedMessage, ChatRoles
from dragiter.domain.ports.llm_service import LLMService, LLMServiceError

logger = logging.getLogger(__name__)


class MockAIService(LLMService):

    def process_query(self, aisp: AIServiceParameters, extended_messages: ExtendedMessages) -> None:
        """
        Simulates an LLM response by echoing the last user message.
        Useful for verifying that prompts and materials were correctly merged.
        """

        logger.debug(f"🔧 (Mock AI SDK) values initialized. Model: {aisp.model_name_string_setting.value}")

        #validation section:

        if not aisp:
            raise MockAIServiceError(f"MockAiService::process_query: AIServiceParameters is None.")

        if not extended_messages:
            raise MockAIServiceError(f"MockAiService::process_query: ExtendedMessages is None.")

        if not extended_messages.extended_message_list:
            raise MockAIServiceError(f"MockAiService::process_query: ExtendedMessages List is None or empty.")

        if len(extended_messages.extended_message_list) == 1:
            raise MockAIServiceError(f"MockAiService::process_query: ExtendedMessages contains only one message (likely the answer container).")


        # generate messages but not the last one (this is the result...)
        input_messages: List[Dict[str, str]] = [
            {"role": msg.role, "content": msg.content}
            for msg in extended_messages.extended_message_list[:-1]
        ]

        output_message: ExtendedMessage =  extended_messages.extended_message_list[-1]


        # Fallback if messages list is empty
        if not input_messages:
            raise MockAIServiceError(f"MockAiService::process_query: Empty input message list.")



        # Get the last message (usually the user prompt with the injected material)
        last_msg = input_messages[-1]
        role = last_msg.get("role", "unknown")
        content = last_msg.get("content", "")



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

        output_message.role = ChatRoles.ASSISTANT
        output_message.content = mock_response

        chat_result = extended_messages.chat_result
        chat_result.started_at = datetime.now()
        chat_result.finish_response = "MOCK_AI"
        chat_result.content = mock_response
        chat_result.ended_at = datetime.now()
        chat_result.duration_ms = (chat_result.ended_at - chat_result.started_at).total_seconds()

        logger.debug(f"Mock AI generated echo for role '{role}'")


class MockAIServiceError(LLMServiceError):
    pass