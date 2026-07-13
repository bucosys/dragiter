# =============================================================================
# dragiter - Deterministic RAG Iterator
# Copyright (c) 2026 Michael Buchold <michael.buchold@dragiter.app>
#
# This file is part of dragiter.
#
# dragiter is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dragiter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with dragiter. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing (closed-source use, SaaS, etc.), please contact:
# Michael Buchold <michael.buchold@dragiter.app>
# =============================================================================

import logging
import time
from datetime import datetime

import openai
from openai import OpenAI

from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.ports.llm_service import LLMService, LLMServiceError

logger = logging.getLogger(__name__)

from typing import TypedDict, List, Dict, Any


# If using Python 3.11+, you can also use NotRequired for individual keys

class OpenAIPayload(TypedDict, total=False):
    """Strict schema for the API payload to prevent string typos."""
    model: str
    messages: list[dict[str, Any]]
    temperature: float
    max_tokens: int
    response_format: dict[str, str]
    # Add other valid OpenAI parameters here


class OpenAIService(LLMService):

    def process_query(self, aisp: AIServiceParameters, chat_session: ChatSession) -> ChatResult:

        attempt: int = 0
        last_exception: Exception | None = None
        retry_delay: int = aisp.retry_delay_int_setting.value or 3
        chat_result = ChatResult()
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

        try:
            # 1. Catch fatal configuration errors immediately (No Retries)
            with OpenAI(api_key=aisp.api_key_string_setting.value,
                        base_url=aisp.base_url_string_setting.value) as client:

                while attempt < (aisp.max_retries_int_setting.value or 1):

                    try:
                        # We store the history locally, as the OpenAI SDK
                        # (unlike genai) does not maintain an internal chat state.
                        response = client.chat.completions.create(**api_kwargs)

                        # Extract answer and save to history
                        answer = response.choices[0].message.content.strip()  # strip() suggested by grok
                        chat_result.output_chat_message.content = answer
                        chat_result.finish_reason = response.choices[0].finish_reason
                        chat_result.input_tokens = response.usage.prompt_tokens
                        chat_result.output_tokens = response.usage.completion_tokens

                        chat_result.ended_at = datetime.now()
                        chat_result.duration_ms = (chat_result.ended_at - chat_result.started_at).total_seconds() * 1000

                        return chat_result

                    except (openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError) as e:
                        last_exception = e
                        attempt += 1

                        # Exponential backoff: 2s, 4s, 8s...
                        wait_time = retry_delay * (2 ** (attempt - 1))
                        logger.warning(
                            f"Studio (OpenAI-SDK): Attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)

                # AFTER some WHILE: final method path
                raise OpenAIServiceError(f"Studio (OpenAI-SDK): Attempt {attempt} failed: {last_exception}")
                # FIX 1: Prevents swallowing our own retry error
        except OpenAIServiceError:
            raise

        except Exception as config_error:
            # We wrap it in your custom error and stop immediately.
            raise OpenAIServiceError(
                f"Studio (OpenAI-SDK): Fatal error or failed to initialize client. Check API key/URL. Details: {config_error}")


class OpenAIServiceError(LLMServiceError):
    pass
