# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""Unit tests for CompletionRetryPolicy and the streaming adapter retry loop."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import openai
import pytest
from support import blank_parameter_groups

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatMessage, ChatSession
from dragiter.domain.models.settings import ValueOrigin
from dragiter.infrastructure.llm.openai_runtime import CompletionRetryPolicy
from dragiter.infrastructure.llm.openai_service_ext import OpenAIServiceError, OpenAIServiceExt

# ---------------------------------------------------------------------------
# Exception factories
# ---------------------------------------------------------------------------


def _request() -> httpx.Request:
    return httpx.Request("POST", "http://example.invalid/v1/chat/completions")


def _response(status_code: int, text: str = "") -> httpx.Response:
    return httpx.Response(status_code, request=_request(), text=text)


def _status_error(
    cls: type[openai.APIStatusError],
    status_code: int,
    message: str = "upstream error",
) -> openai.APIStatusError:
    """Build an SDK status error without talking to a network."""
    return cls(message, response=_response(status_code, message), body={"error": message})


def _connection_error(message: str = "connection reset") -> openai.APIConnectionError:
    return openai.APIConnectionError(message=message, request=_request())


def _timeout_error() -> openai.APITimeoutError:
    return openai.APITimeoutError(request=_request())


# ---------------------------------------------------------------------------
# Policy: classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (lambda: _status_error(openai.InternalServerError, 500), True),
        (lambda: _status_error(openai.InternalServerError, 502), True),
        (lambda: _status_error(openai.InternalServerError, 503), True),
        (lambda: _status_error(openai.RateLimitError, 429), True),
        (lambda: _connection_error(), True),
        (lambda: _status_error(openai.InternalServerError, 504), False),
        (
            lambda: _status_error(
                openai.InternalServerError, 504, "Gateway Timeout"
            ),
            False,
        ),
        (
            lambda: _status_error(
                openai.APIStatusError, 502, "stream timeout from proxy"
            ),
            False,
        ),
        (
            lambda: _status_error(
                openai.InternalServerError,
                500,
                "the model runner has unexpectedly stopped",
            ),
            False,
        ),
        (lambda: _timeout_error(), False),
        (lambda: _status_error(openai.BadRequestError, 400), False),
        (lambda: _status_error(openai.AuthenticationError, 401), False),
        (lambda: _status_error(openai.PermissionDeniedError, 403), False),
        (lambda: _status_error(openai.NotFoundError, 404), False),
        (lambda: RuntimeError("unrelated"), False),
    ],
    ids=[
        "http-500",
        "http-502",
        "http-503",
        "http-429",
        "connection",
        "http-504",
        "gateway-timeout-text",
        "stream-timeout-text",
        "runner-crash",
        "api-timeout",
        "http-400",
        "http-401",
        "http-403",
        "http-404",
        "unrelated",
    ],
)
def test_is_retryable_classifies_known_faults(factory, expected: bool) -> None:
    """Covers EXEC-09, EXEC-10."""
    policy = CompletionRetryPolicy()
    assert policy.is_retryable(factory()) is expected


def test_max_attempts_honours_setting() -> None:
    """Covers EXEC-06, EXEC-07."""
    groups = blank_parameter_groups()
    aisp = groups["aisp"]
    policy = CompletionRetryPolicy()

    assert policy.max_attempts(aisp) == 1

    aisp.max_retries_int_setting.set(3, ValueOrigin.CLI)
    assert policy.max_attempts(aisp) == 3


def test_wait_seconds_is_zero_on_first_attempt() -> None:
    """Covers EXEC-08."""
    policy = CompletionRetryPolicy()
    assert policy.wait_seconds(1, retry_delay=5) == 0
    assert policy.wait_seconds(2, retry_delay=5) == 5
    assert policy.wait_seconds(3, retry_delay=5) == 10


# ---------------------------------------------------------------------------
# Adapter loop
# ---------------------------------------------------------------------------


def _query_params(*, max_retry: int = 3, retry_delay: int = 0) -> tuple[Any, Any, ChatSession]:
    groups = blank_parameter_groups()
    aisp = groups["aisp"]
    lp = groups["lp"]
    aisp.api_key_string_setting.set("test-key", ValueOrigin.CLI)
    aisp.base_url_string_setting.set("http://example.invalid/v1", ValueOrigin.CLI)
    aisp.model_name_string_setting.set("test-model", ValueOrigin.CLI)
    aisp.max_retries_int_setting.set(max_retry, ValueOrigin.CLI)
    aisp.retry_delay_int_setting.set(retry_delay, ValueOrigin.CLI)
    lp.verbose_bool_setting.set(False, ValueOrigin.CLI)
    session = ChatSession(input_chat_message_list=[ChatMessage(role="user", content="ping")])
    return aisp, lp, session


class _ClientCM:
    """Stand-in for ``openai.OpenAI`` used as a context manager."""

    def __enter__(self) -> _ClientCM:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _service_with_mocked_transport(monkeypatch: pytest.MonkeyPatch) -> OpenAIServiceExt:
    transport = MagicMock()
    transport.create.return_value = MagicMock()
    monkeypatch.setattr(
        "dragiter.infrastructure.llm.openai_service_ext.OpenAI",
        lambda **kwargs: _ClientCM(),
    )
    return OpenAIServiceExt(transport_factory=transport)


def test_process_query_retries_transient_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """Covers EXEC-11."""
    service = _service_with_mocked_transport(monkeypatch)
    calls = {"n": 0}
    result = ChatResult()

    def consume(*_args: object, **_kwargs: object) -> ChatResult:
        calls["n"] += 1
        if calls["n"] < 3:
            raise _status_error(openai.InternalServerError, 503, "temporarily overloaded")
        return result

    monkeypatch.setattr(service, "_consume_stream", consume)
    monkeypatch.setattr("dragiter.infrastructure.llm.openai_service_ext.time.sleep", lambda *_: None)

    aisp, lp, session = _query_params(max_retry=3)
    assert service.process_query(aisp, lp, session) is result
    assert calls["n"] == 3


def test_process_query_does_not_retry_504(monkeypatch: pytest.MonkeyPatch) -> None:
    """Covers EXEC-12."""
    service = _service_with_mocked_transport(monkeypatch)
    calls = {"n": 0}

    def consume(*_args: object, **_kwargs: object) -> ChatResult:
        calls["n"] += 1
        raise _status_error(openai.InternalServerError, 504, "Gateway Timeout")

    monkeypatch.setattr(service, "_consume_stream", consume)

    aisp, lp, session = _query_params(max_retry=5)
    with pytest.raises(OpenAIServiceError, match="gateway"):
        service.process_query(aisp, lp, session)
    assert calls["n"] == 1


def test_process_query_stops_after_max_attempts_on_500(monkeypatch: pytest.MonkeyPatch) -> None:
    """Covers EXEC-13."""
    service = _service_with_mocked_transport(monkeypatch)
    calls = {"n": 0}

    def consume(*_args: object, **_kwargs: object) -> ChatResult:
        calls["n"] += 1
        raise _status_error(openai.InternalServerError, 500, "backend fault")

    monkeypatch.setattr(service, "_consume_stream", consume)
    monkeypatch.setattr("dragiter.infrastructure.llm.openai_service_ext.time.sleep", lambda *_: None)

    aisp, lp, session = _query_params(max_retry=3)
    with pytest.raises(OpenAIServiceError, match="Attempt 3/3"):
        service.process_query(aisp, lp, session)
    assert calls["n"] == 3
