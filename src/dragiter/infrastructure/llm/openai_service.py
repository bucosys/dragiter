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
import ssl
import time
from datetime import datetime

import httpx
import openai
from openai import OpenAI

from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.ports.llm_service import LLMService, LLMServiceError

logger = logging.getLogger(__name__)

from typing import TypedDict, Any


class OpenAIPayload(TypedDict, total=False):
    model: str
    messages: list[dict[str, Any]]
    temperature: float
    max_tokens: int
    response_format: dict[str, str]


class OpenAIService(LLMService):

    def process_query(self, aisp: AIServiceParameters, chat_session: ChatSession) -> ChatResult:

        attempt: int = 0
        last_exception: Exception | None = None
        retry_delay: int = aisp.retry_delay_int_setting.value or 3
        wait_time: int = retry_delay #initial
        chat_result = ChatResult()
        chat_result.started_at = datetime.now()

        logger.debug(f"(OpenAI SDK) Model: {aisp.model_name_string_setting.value}")

        dict_list = [
            {"role": msg.role, "content": msg.content}
            for msg in chat_session.input_chat_message_list
        ]

        api_kwargs: OpenAIPayload = {
            "model": aisp.model_name_string_setting.value,
            "messages": dict_list
        }

        if aisp.temperature_float_setting.is_set:
            api_kwargs["temperature"] = aisp.temperature_float_setting.value
        if aisp.max_output_tokens_int_setting.is_set:
            api_kwargs["max_tokens"] = aisp.max_output_tokens_int_setting.value

        http_client: httpx.Client | None = None

        try:
            client_kwargs: dict[str, Any] = {
                "api_key": aisp.api_key_string_setting.value,
                "base_url": aisp.base_url_string_setting.value,
            }

            # --- TLS / mTLS Konfiguration ---------------------------------
            verify: bool | str | ssl.SSLContext = True
            cert = None

            if aisp.ca_bundle_file_path_setting.is_set:
                ca_path = str(aisp.ca_bundle_file_path_setting.value)
                logger.debug(f"Using custom CA bundle: {ca_path}")
                verify = ca_path

            if aisp.client_cert_file_path_setting.is_set:
                cert_path = str(aisp.client_cert_file_path_setting.value)

                if aisp.client_key_file_path_setting.is_set:
                    key_path = str(aisp.client_key_file_path_setting.value)
                    logger.debug("mTLS: Using client cert + separate key")

                    # Expliziter SSLContext – das ist der entscheidende Fix
                    ctx = ssl.create_default_context(
                        cafile=ca_path if aisp.ca_bundle_file_path_setting.is_set else None)
                    ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
                    verify = ctx
                    cert = None  # schon im Context geladen
                else:
                    cert = cert_path
                    logger.debug("mTLS: Using combined client cert file")

            http_client = httpx.Client(verify=verify, cert=cert)
            client_kwargs["http_client"] = http_client
            # --------------------------------------------------------------

            with OpenAI(**client_kwargs) as client:

                while attempt < (aisp.max_retries_int_setting.value or 1):
                    try:
                        if attempt > 0: time.sleep(wait_time)
                        response = client.chat.completions.create(**api_kwargs)

                        answer = response.choices[0].message.content.strip()
                        chat_result.output_chat_message.content = answer
                        chat_result.finish_reason = response.choices[0].finish_reason
                        chat_result.input_tokens = response.usage.prompt_tokens
                        chat_result.output_tokens = response.usage.completion_tokens

                        chat_result.ended_at = datetime.now()
                        chat_result.duration_ms = (
                            chat_result.ended_at - chat_result.started_at
                        ).total_seconds() * 1000

                        return chat_result

                    except (openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError) as e:
                        last_exception = e
                        attempt += 1
                        wait_time = retry_delay * (2 ** (attempt - 1))
                        logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {wait_time}s...")


                raise OpenAIServiceError(f"Attempt {attempt} failed: {last_exception}")

        except OpenAIServiceError:
            raise
        except Exception as e:
            raise OpenAIServiceError(
                f"Failed to initialize OpenAI client (check CA-bundle / client cert / key). Details: {e}"
            ) from e
        finally:
            if http_client is not None:
                http_client.close()


class OpenAIServiceError(LLMServiceError):
    pass