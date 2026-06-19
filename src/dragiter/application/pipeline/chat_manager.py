from dragiter.application.core.xdi import *
from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.chat_results import ChatResults, ChatResult
from dragiter.domain.models.chat_sessions import ChatSessions
from dragiter.domain.models.settings import SimulateBoolSetting
from dragiter.domain.ports.llm_service import LLMService
from dragiter.infrastructure.llm.mockai_service import MockAIService

logger = logging.getLogger(__name__)


class ChatManager:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    def run(self,
            ai_service_parameter: AIServiceParameters,
            chat_sessions: ChatSessions,
            simulation_boolean_setting: SimulateBoolSetting,
            ) -> ChatResults:

        chat_result_list: list[ChatResult] = []

        try:

            # use the mock service if simulation process requested
            if simulation_boolean_setting.value:
                self.llm_service = MockAIService()

            for session in chat_sessions.session_list:
                chat_result_list.append(self.llm_service.process_query(ai_service_parameter, session))

            return ChatResults(chat_result_list)

        except Exception as e:
            raise ChatManagerError(f"Failed to process openai query: {e}") from e


class ChatManagerError(Exception):
    pass
