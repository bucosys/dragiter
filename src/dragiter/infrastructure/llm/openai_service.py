import logging
import time
from typing import List, Dict

from openai import OpenAI

from dragiter.domain.ports.llm_service_protocol import LLMServiceProtocol

logger = logging.getLogger(__name__)

class OpenAIService(LLMServiceProtocol):
    def __init__(self, api_key: str, base_url: str, model_name: str, temperature: float=0.0):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = temperature

        self.max_retries = 3

        logger.debug(f"🔧 (OpenAI SDK) values initialized. Model: {self.model_name}")



    def ask(self, messages: List[Dict[str, str]] = []) -> str:

        attempt = 0
        while attempt < self.max_retries:

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

                attempt += 1
                if attempt >= self.max_retries:
                    logger.error(f"Studio (OpenAI-SDK) Final Error after {self.max_retries} attempts: {e}")
                    return f"Error: {e}"

                # Exponential backoff: 2s, 4s, 8s...
                wait_time = self.retry_delay * (2 ** (attempt - 1))
                logger.warning(f"Studio (OpenAI-SDK) Attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)


                logger.error(f"Studio (OpenAI-SDK) Error: {e}")
                return f"Error: {e}"


class OpenAI_Service_Error(Exception):
    pass