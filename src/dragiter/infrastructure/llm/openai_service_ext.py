# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold#
# openai_service_ext.py
# Extended version of OpenAIService with:
#   1. Always-on streaming
#   2. Progress heartbeat via the logger (when verbose is active)
#   3. Optional TCP Keepalive (new parameter)
#
# Drop-in replacement for the original openai_service.py
# =============================================================================

from collections.abc import Iterator
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

    def _log_progress(self) -> Iterator[str]:
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

    def _create_client(
        self, aisp: AIServiceParameters
    ) -> tuple[DefaultHttpx2Client, OpenAI]:
        """Build transport and SDK client. Failures here are initialisation errors."""
        try:
            http_client = self._transport_factory.create(aisp)
            client = OpenAI(
                api_key=aisp.api_key_string_setting.value,
                base_url=aisp.base_url_string_setting.value,
                http_client=http_client,
                max_retries=0,
            )
        except Exception as exc:
            raise OpenAIServiceError(
                "Failed to initialise OpenAI client "
                f"(check CA-bundle / client cert / key). Details: {exc}"
            ) from exc
        return http_client, client

    def process_query(
        self, aisp: AIServiceParameters, lp: LoggingParameters, chat_session: ChatSession
    ) -> ChatResult:
        retry_delay: int = aisp.retry_delay_int_setting.value or 3
        max_attempts = self._retry_policy.max_attempts(aisp)
        last_exception: Exception | None = None

        chat_result = ChatResult()
        chat_result.started_at = datetime.now()

        logger.debug("(OpenAI SDK) Model: %s", aisp.model_name_string_setting.value)

        api_kwargs = self._build_payload(aisp, chat_session)
        http_client, client = self._create_client(aisp)
        progress = self._log_progress()

        try:
            with client:
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
                            client, api_kwargs, lp, progress, chat_result
                        )
                    except (
                        openai.APIConnectionError,
                        openai.APIStatusError,
                    ) as exc:
                        last_exception = exc
                        detail = self._retry_policy.describe(exc)
                        if not self._retry_policy.is_retryable(exc) or attempt >= max_attempts:
                            raise OpenAIServiceError(
                                f"Attempt {attempt}/{max_attempts} failed: {detail}"
                            ) from exc
                        logger.warning(
                            "Attempt %s/%s failed: %s",
                            attempt,
                            max_attempts,
                            detail,
                        )
                    except Exception as exc:
                        raise OpenAIServiceError(
                            f"Attempt {attempt}/{max_attempts} failed: {exc}"
                        ) from exc

            raise OpenAIServiceError(
                f"Attempt {max_attempts}/{max_attempts} failed: {last_exception}"
            )
        finally:
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
        progress: Iterator[str],
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
