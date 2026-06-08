import logging
from datetime import datetime
from typing import List, Dict

from dragiter.domain.models.ai_service_parameters import AIServiceParameters

from dragiter.domain.models.chat_sessions import ChatMessage, ChatRoles

from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.ports.llm_service import LLMService, LLMServiceError

logger = logging.getLogger(__name__)


class MockAIService(LLMService):

    def process_query(self, aisp: AIServiceParameters, chat_session: ChatSession) -> ChatSession:
        """
        Simulates an LLM response by echoing the last user message.
        Useful for verifying that prompts and materials were correctly merged.
        """

        logger.debug(f"🔧 (Mock AI SDK) values initialized. Model: {aisp.model_name_string_setting.value}")

        #validation section:

        if not aisp:
            raise MockAIServiceError(f"MockAiService::process_query: AIServiceParameters is None.")

        if not chat_session:
            raise MockAIServiceError(f"MockAiService::process_query: ChatSession is None.")

        if not chat_session.input_chat_message_list:
            raise MockAIServiceError(f"MockAiService::process_query: Input chat message list is None or empty.")

        try:
            chat_session.input_chat_message_list[0]

            # Get the last message (usually the user prompt with the injected material)
            last_msg = chat_session.input_chat_message_list[-1]
            role = last_msg.role or ""
            content = last_msg.content or ""



            # Create a detailed response for debugging
            mock_response = (
                f"[START MOCK AI RESPONSE ({aisp.model_name_string_setting.value})]\n"
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Detected Role: {role}\n"
                f"Content Preview: {content[:50]}...\n"
                f"--- FULL CONTENT ECHO ---\n"
                f"{content}\n"
                f"[END OF MOCK]"
            )

            chat_session.output_chat_message.content = mock_response

            chat_result = chat_session.chat_result
            chat_result.started_at = datetime.now()
            chat_result.finish_response = "MOCK_AI"
            chat_result.content = mock_response
            chat_result.ended_at = datetime.now()
            chat_result.duration_ms = (chat_result.ended_at - chat_result.started_at).total_seconds()

            logger.debug(f"Mock AI generated echo for role '{role}'")
            return chat_session

        except Exception as e:
            raise MockAIServiceError(f"Failed to process mock service: {e}") from e




class MockAIServiceError(LLMServiceError):
    pass