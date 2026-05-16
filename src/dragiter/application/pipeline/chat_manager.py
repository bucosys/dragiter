from dragiter.application.core.xdi import *
from dragiter.domain.models.conversation_history import ConversationHistory
from dragiter.infrastructure.llm.llm_service_adapter import LLMServiceAdapter

logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self) -> None:
        pass


    def run(self,
            llm_service_adapter: LLMServiceAdapter,
            conversation_history: ConversationHistory,
            ) -> ConversationHistory:


        try:

            agent = llm_service_adapter

            messages = []

            while messages := conversation_history.build_chat_prompt_dict_list():
                answer1 = agent.ask(messages)
                conversation_history.update_assistant_content((answer1 or "").strip())
                messages = []




        except Exception as e:
            raise ChatManagerError(f"Failed to process openai query") from e

        finally:
            return conversation_history



class ChatManagerError(Exception):
    pass