import logging
import time
from datetime import datetime
from typing import List, Dict

from openai import OpenAI

from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.ports.llm_service import LLMService, LLMServiceError

logger = logging.getLogger(__name__)



from typing import TypedDict, List, Dict, Any
# If using Python 3.11+, you can also use NotRequired for individual keys

class OpenAIPayload(TypedDict, total=False):
    """Strict schema for the API payload to prevent string typos."""
    model: str
    messages: List[Dict[str, Any]]
    temperature: float
    max_tokens: int
    response_format: Dict[str, str]
    # Add other valid OpenAI parameters here



class OpenAIService(LLMService):

    def process_query(self, aisp: AIServiceParameters, chat_session: ChatSession) -> ChatSession:

        attempt:int = 0
        last_exception: Exception | None = None
        retry_delay: int = aisp.retry_delay_int_setting.value or 3
        chat_result = chat_session.chat_result
        chat_result.started_at = datetime.now()

        logger.debug(f"(OpenAI SDK) values initialized. Model: {aisp.model_name_string_setting.value}")

        # ... inside your adapter method ...
        # Result: [{"role": "user", "content": "Hello"}, ...]
        dict_list = [
            {"role": msg.role, "content": msg.content}
            for msg in chat_session.input_chat_message_list
        ]


        # 1. Type-hint the dictionary upon creation
        api_kwargs: OpenAIPayload = {
            "model": aisp.model_name_string_setting.value,
            "messages": dict_list
        }

        # 2. Dynamic injection
        if aisp.temperature_float_setting.is_set:
            api_kwargs["temperature"] = aisp.temperature_float_setting.value

        if aisp.max_output_tokens_int_setting.is_set:
            # If you type "max_token" here by mistake, your IDE (and mypy)
            # will instantly throw a red underline and fail the build.
            api_kwargs["max_tokens"] = aisp.max_output_tokens_int_setting.value


        while attempt < (aisp.max_retries_int_setting.value or 1):

            try:
                # Initialization of the OpenAI client
                client = OpenAI(
                    api_key=aisp.api_key_string_setting.value,
                    base_url=aisp.base_url_string_setting.value)

                # We store the history locally, as the OpenAI SDK
                # (unlike genai) does not maintain an internal chat state.
                response = client.chat.completions.create(**api_kwargs)


                # Extract answer and save to history
                answer = response.choices[0].message.content.strip() # strip() suggested by grok
                chat_session.output_chat_message.content = answer or ""
                chat_result.content = answer
                chat_result.finish_reason = response.choices[0].finish_reason
                chat_result.input_tokens = response.usage.prompt_tokens
                chat_result.output_tokens = response.usage.completion_tokens

                chat_result.ended_at = datetime.now()
                chat_result.duration_ms = (chat_result.ended_at - chat_result.started_at).total_seconds()

                return chat_result


            except Exception as e:
                last_exception = e
                attempt += 1

                # Exponential backoff: 2s, 4s, 8s...
                wait_time = retry_delay * (2 ** (attempt - 1))
                logger.warning(f"Studio (OpenAI-SDK): Attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

        #final method path
        raise OpenAIServiceError(f"Studio (OpenAI-SDK): Attempt {attempt} failed: {last_exception}")



class OpenAIServiceError(LLMServiceError):
    pass