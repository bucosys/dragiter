from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.settings import MaxOutputTokensIntSetting, SimulateBoolSetting, CharsPerTokenFloatSetting
from dragiter.application.core.xdi import *
from dragiter.domain.models.conversation_history import ConversationHistory
from dragiter.domain.ports.llm_service import LLMService
from dragiter.infrastructure.llm.llm_service_adapter import LLMServiceAdapter

from dragiter.domain.ports.payload_estimator import PayloadEstimator
from dragiter.infrastructure.llm.mockai_service import MockAIService

logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service


    def run(self,
            ai_service_parameter: AIServiceParameters,
            conversation_history: ConversationHistory,
            simulation_boolean_setting: SimulateBoolSetting,
           ) -> ConversationHistory:


        try:

            # use the mock service if simulation process requested
            if simulation_boolean_setting.value:
                self.llm_service = MockAIService()


            while messages := conversation_history.build_chat_prompt_dict_list():
                answer1 = self.llm_service.process_query(ai_service_parameter, messages)
                conversation_history.update_assistant_content((answer1.content or "").strip())




        except Exception as e:
            raise ChatManagerError(f"Failed to process openai query: {e}") from e

        finally:
            return conversation_history



class ChatManagerError(Exception):
    pass