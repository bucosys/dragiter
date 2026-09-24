# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""Unit tests for the streaming adapter retry loop and error wrapping."""

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


def test_init_failure_is_labelled_as_initialisation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers EXEC-14."""
    transport = MagicMock()
    transport.create.side_effect = OSError("bad CA bundle")
    service = OpenAIServiceExt(transport_factory=transport)

    aisp, lp, session = _query_params()
    with pytest.raises(OpenAIServiceError, match="initialise OpenAI client") as captured:
        service.process_query(aisp, lp, session)
    assert "bad CA bundle" in str(captured.value)


def test_unexpected_stream_error_is_not_labelled_as_initialisation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers EXEC-15."""
    service = _service_with_mocked_transport(monkeypatch)

    def consume(*_args: object, **_kwargs: object) -> ChatResult:
        raise RuntimeError("chunk exploded")

    monkeypatch.setattr(service, "_consume_stream", consume)

    aisp, lp, session = _query_params()
    with pytest.raises(OpenAIServiceError, match="chunk exploded") as captured:
        service.process_query(aisp, lp, session)
    assert "initialise" not in str(captured.value).lower()


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


def test_process_query_stops_after_max_attempts_on_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (lambda: _status_error(openai.InternalServerError, 500), True),
        (lambda: _status_error(openai.InternalServerError, 502), True),
        (lambda: _status_error(openai.InternalServerError, 503), True),
        (lambda: _status_error(openai.InternalServerError, 504), False),
        (lambda: _status_error(openai.RateLimitError, 429), True),
        (lambda: _status_error(openai.BadRequestError, 400), False),
    ],
)
def test_retry_policy_matches_adapter_loop(factory, expected: bool) -> None:
    """Covers EXEC-09, EXEC-10."""
    assert CompletionRetryPolicy().is_retryable(factory()) is expected
