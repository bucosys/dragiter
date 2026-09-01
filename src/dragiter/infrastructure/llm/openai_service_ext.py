# =============================================================================
# dragiter - Deterministic Context Iterator
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
#
# openai_service_ext.py
# Extended version of OpenAIService with:
#   1. Always-on streaming
#   2. Progress spinner on stderr (when verbose is active)
#   3. Optional TCP Keepalive (new parameter)
#
# Drop-in replacement for the original openai_service.py
# =============================================================================

from datetime import datetime
import logging
import time
from typing import Any, TypedDict

import openai
from openai import DefaultHttpx2Client, OpenAI

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import AIServiceParameters, LoggingParameters
from dragiter.domain.ports.llm_service import LLMService, LLMServiceError
from dragiter.infrastructure.llm.openai_runtime import (
    CompletionRetryPolicy,
    OpenAITransportFactory,
)

logger = logging.getLogger(__name__)

_PROGRESS_INTERVAL_SECONDS = 10.0
_PROGRESS_WATCHES = "🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛"


class OpenAIPayload(TypedDict, total=False):
    model: str
    messages: list[dict[str, Any]]
    temperature: float
    max_tokens: int
    response_format: dict[str, str]
    stream: bool


class OpenAIServiceError(LLMServiceError):
    pass


class OpenAIServiceExt(LLMService):
    """Streaming OpenAI-compatible adapter. Orchestrates transport + retry policy."""

    def __init__(
        self,
        transport_factory: OpenAITransportFactory | None = None,
        retry_policy: CompletionRetryPolicy | None = None,
    ) -> None:
        self._transport_factory = transport_factory or OpenAITransportFactory()
        self._retry_policy = retry_policy or CompletionRetryPolicy()

    def _log_progress(self):
        """Yield a heartbeat glyph; log at most once every ten seconds."""
        index = 0
        current = _PROGRESS_WATCHES[0]
        last_emitted = time.monotonic()

        while True:
            now = time.monotonic()
            if now - last_emitted < _PROGRESS_INTERVAL_SECONDS:
                yield current
                continue

            current = _PROGRESS_WATCHES[index]
            logger.info("Still running %s", current)
            last_emitted = now
            index = (index + 1) % len(_PROGRESS_WATCHES)
            yield current

    def _print_watch(self):
        watches: str = "🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛"
        i: int = 0
        last: float = 0.0
        now: float = 0.0
        while True:
            now = time.monotonic()
            if last and now - last < 1.0:
                yield watches[(i - 1) % len(watches)]
                continue

            print(f"\r{watches[i]}", end="", flush=True)
            last = now
            current = watches[i]
            i = (i + 1) % len(watches)
            yield current

    def process_query(
        self, aisp: AIServiceParameters, lp: LoggingParameters, chat_session: ChatSession
    ) -> ChatResult:
        retry_delay: int = aisp.retry_delay_int_setting.value or 3
        max_attempts = self._retry_policy.max_attempts(aisp)
        last_exception: Exception | None = None

        chat_result = ChatResult()
        chat_result.started_at = datetime.now()

        logger.debug(f"(OpenAI SDK) Model: {aisp.model_name_string_setting.value}")

        api_kwargs = self._build_payload(aisp, chat_session)
        http_client: DefaultHttpx2Client | None = None

        try:
            http_client = self._transport_factory.create(aisp)
            pw = self._log_progress()

            with OpenAI(
                api_key=aisp.api_key_string_setting.value,
                base_url=aisp.base_url_string_setting.value,
                http_client=http_client,
                max_retries=0,
            ) as client:
                for attempt in range(1, max_attempts + 1):
                    wait_time = self._retry_policy.wait_seconds(attempt, retry_delay)
                    if wait_time:
                        logger.warning(
                            "Retrying in %ss (attempt %s/%s)",
                            wait_time,
                            attempt,
                            max_attempts,
                        )
                        time.sleep(wait_time)

                    try:
                        return self._consume_stream(
                            client, api_kwargs, lp, pw, chat_result
                        )
                    except (
                        openai.RateLimitError,
                        openai.APIConnectionError,
                        openai.APITimeoutError,
                        openai.APIStatusError,
                        openai.InternalServerError,
                    ) as e:
                        last_exception = e
                        detail = self._retry_policy.describe(e)
                        if not self._retry_policy.is_retryable(e) or attempt >= max_attempts:
                            raise OpenAIServiceError(
                                f"Attempt {attempt}/{max_attempts} failed: {detail}"
                            ) from e
                        logger.warning(
                            "Attempt %s/%s failed: %s",
                            attempt,
                            max_attempts,
                            detail,
                        )

            raise OpenAIServiceError(
                f"Attempt {max_attempts}/{max_attempts} failed: {last_exception}"
            )

        except OpenAIServiceError:
            raise
        except Exception as e:
            raise OpenAIServiceError(
                f"Failed to initialize OpenAI client (check CA-bundle / client cert / key). Details: {e}"
            ) from e
        finally:
            if http_client is not None:
                http_client.close()

    def _build_payload(
        self, aisp: AIServiceParameters, chat_session: ChatSession
    ) -> OpenAIPayload:
        payload: OpenAIPayload = {
            "model": aisp.model_name_string_setting.value,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in chat_session.input_chat_message_list
            ],
            "stream": True,
        }
        if aisp.temperature_float_setting.is_set:
            payload["temperature"] = aisp.temperature_float_setting.value
        if aisp.max_output_tokens_int_setting.is_set:
            payload["max_tokens"] = aisp.max_output_tokens_int_setting.value
        return payload

    def _consume_stream(
        self,
        client: OpenAI,
        api_kwargs: OpenAIPayload,
        lp: LoggingParameters,
        progress,
        chat_result: ChatResult,
    ) -> ChatResult:
        stream = client.chat.completions.create(**api_kwargs)

        content_parts: list[str] = []
        finish_reason: str | None = None
        input_tokens = 0
        output_tokens = 0

        for chunk in stream:
            if lp.verbose_bool_setting.value:
                next(progress)

            if not chunk.choices:
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    input_tokens = getattr(chunk.usage, "prompt_tokens", 0) or 0
                    output_tokens = getattr(chunk.usage, "completion_tokens", 0) or 0
                continue

            delta = chunk.choices[0].delta
            if delta and delta.content:
                content_parts.append(delta.content)

            if chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason

            if hasattr(chunk, "usage") and chunk.usage is not None:
                input_tokens = getattr(chunk.usage, "prompt_tokens", 0) or 0
                output_tokens = getattr(chunk.usage, "completion_tokens", 0) or 0

        chat_result.output_chat_message.content = "".join(content_parts).strip()
        chat_result.finish_reason = finish_reason or "stop"
        chat_result.input_tokens = input_tokens
        chat_result.output_tokens = output_tokens
        chat_result.ended_at = datetime.now()
        chat_result.duration_ms = (
            chat_result.ended_at - chat_result.started_at
        ).total_seconds() * 1000
        return chat_result
