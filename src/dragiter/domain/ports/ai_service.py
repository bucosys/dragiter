import logging
from typing import List, Dict

from openai import OpenAI

from dragiter.domain.models import LLMServiceProtocol

logger = logging.getLogger(__name__)

class AIService(LLMServiceProtocol):
    def __init__(self, api_key: str, base_url: str, model_name: str, temperature: float=0.0):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = temperature

        try
            _init_transform()
            _init_validate()


    def ask(self, messages: List[Dict[str, str]] = []) -> str:
        try:
            # Initialization of the OpenAI client
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            # We store the history locally, as the OpenAI SDK
            # (unlike genai) does not maintain an internal chat state.
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature
            )


            # Extract answer and save to history
            answer = response.choices[0].message.content
            return answer

        except Exception as e:
            logger.error(f"Studio (OpenAI-SDK) Error: {e}")
            return f"Error: {e}"



    def deprecated_ask(self, task: str, instruction: str = None) -> str:
        chat_history = []
        try:
            # Initialization of the OpenAI client
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            # We store the history locally, as the OpenAI SDK
            # (unlike genai) does not maintain an internal chat state.

            # Add message to history, first instruction
            if len(chat_history) == 0 and instruction:
                chat_history.append({"role": "system", "content": instruction})

            # then task
            chat_history.append({"role": "user", "content": task}) # there is no self.chat_history

            response = client.chat.completions.create(
                model=self.model_name,
                messages=chat_history
            )

            # Extract answer and save to history
            answer = response.choices[0].message.content
            chat_history.append({"role": "assistant", "content": answer})

            return answer
        except Exception as e:
            raise OpenAI_Service_Error(f"Failed to load prompt.") from e


class AI_Service_Error(Exception):
    pass