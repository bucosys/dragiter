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

"""
Unit tests for ContextWindowEstimator.

These tests are fully isolated: no CLI subprocess, no Ollama, no file I/O.
The PayloadEstimator dependency is replaced with a small in-memory test
double, so the whole suite runs in milliseconds and belongs in every CI run.

Regression context:
A previous release shipped two `debug(...)` calls in ContextWindowEstimator
where `logger.debug(...)` was intended. `debug` was not defined anywhere in
that module, so every call path that reached those lines raised a bare
NameError, which was then swallowed and re-wrapped by the broad
`except Exception` in `run()` as a misleading ContextWindowValidatorError
("... due to that reason: name 'debug' is not defined"). The bug was only
discovered by chance during a manual, non-CI functional test run against a
live Ollama instance.

test_run_raises_when_limit_exceeded_and_not_simulating() and
test_run_does_not_raise_in_verbose_mode() specifically exercise both former
call sites (the unconditional one and the verbose-gated one) and assert that
no such NameError text ever resurfaces. That way, if this bug is ever
reintroduced, it fails loudly and immediately in a fast unit test instead of
silently in production.
"""

import pytest

from dragiter.application.pipeline.context_window_estimator import (
    ContextWindowEstimator,
    ContextWindowValidatorError,
)
from dragiter.domain.models.chat_sessions import ChatMessage, ChatSession, ChatSessions
from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExcecutionParameters,
    LoggingParameters,
)
from dragiter.domain.models.settings import (
    ActivityFilePathSetting,
    APIKeyStringSetting,
    BaseURLStringSetting,
    CaBundleFilePathSetting,
    CharsPerTokenFloatSetting,
    ClientCertFilePathSetting,
    ClientKeyFilePathSetting,
    DebugBoolSetting,
    LogFilePathSetting,
    MaxContextTokensIntSetting,
    MaxOutputTokensIntSetting,
    MaxRetryIntSetting,
    ModelNameStringSetting,
    RetryDelayIntSetting,
    SequentialProcessingBoolSetting,
    SimulateBoolSetting,
    TCPKeepAliveBoolSetting,
    TemperatureFloatSetting,
    ValueOrigin,
    VerboseBoolSetting,
)

# ---------------------------------------------------------------------------
# Test doubles / helpers
# ---------------------------------------------------------------------------


class StubPayloadEstimator:
    """
    Minimal stand-in for the real PayloadEstimator (see domain.ports.payload_estimator).

    `tokens` can be either:
      - an int: every call to `estimate()` returns the same fixed value
      - a list[int]: one value is returned per call, in order (useful for
        simulating several chat sessions with different sizes)

    All calls are recorded in `.calls` so tests can assert the estimator was
    (or was not) invoked at all.
    """

    def __init__(self, tokens):
        self._tokens = tokens
        self._call_index = 0
        self.calls: list[tuple[list[ChatMessage], float]] = []

    def estimate(self, chat_messages: list[ChatMessage], chars_per_token: float) -> int:
        self.calls.append((chat_messages, chars_per_token))
        if isinstance(self._tokens, list):
            value = self._tokens[self._call_index]
            self._call_index += 1
            return value
        return self._tokens


def make_settings(
    *,
    chars_per_token: float = 4.0,
    max_context_tokens: int = 1000,
    max_output_tokens: int = 200,
    verbose: bool = False,
    simulate: bool = False,
    prerequisites_unset: bool = False,
) -> tuple[AIServiceParameters, LoggingParameters, ExcecutionParameters]:
    """
    Build parameter groups for a single `run()` call.

    Each ValueSetting instance can only be assigned once, so every test
    must call this factory anew rather than reusing settings across calls.
    """
    chars_per_token_setting = CharsPerTokenFloatSetting("chars_per_token")
    max_context_tokens_setting = MaxContextTokensIntSetting("max_context_tokens")
    max_output_tokens_setting = MaxOutputTokensIntSetting("max_output_tokens")
    verbose_setting = VerboseBoolSetting("verbose")
    simulate_setting = SimulateBoolSetting("simulate")

    verbose_setting.set(verbose, ValueOrigin.CLI)
    simulate_setting.set(simulate, ValueOrigin.CLI)

    if not prerequisites_unset:
        chars_per_token_setting.set(chars_per_token, ValueOrigin.CLI)
        max_context_tokens_setting.set(max_context_tokens, ValueOrigin.CLI)
        max_output_tokens_setting.set(max_output_tokens, ValueOrigin.CLI)

    aisp = AIServiceParameters(
        APIKeyStringSetting("api_key"),
        TCPKeepAliveBoolSetting("tcp_keep_alive"),
        BaseURLStringSetting("base_url"),
        ModelNameStringSetting("model_name"),
        max_context_tokens_setting,
        max_output_tokens_setting,
        chars_per_token_setting,
        TemperatureFloatSetting("temperature"),
        RetryDelayIntSetting("retry_delay"),
        MaxRetryIntSetting("max_retry"),
        CaBundleFilePathSetting("ca_bundle_file"),
        ClientCertFilePathSetting("client_cert_file"),
        ClientKeyFilePathSetting("client_key_file"),
    )
    lp = LoggingParameters(
        DebugBoolSetting("debug"),
        verbose_setting,
        LogFilePathSetting("log_file"),
        ActivityFilePathSetting("activity_file"),
    )
    ep = ExcecutionParameters(
        simulate_setting,
        SequentialProcessingBoolSetting("sequential_processing"),
    )
    return aisp, lp, ep


def make_chat_sessions(num_sessions: int = 1) -> ChatSessions:
    """Build `num_sessions` trivial single-message chat sessions."""
    sessions = [
        ChatSession(
            input_chat_message_list=[ChatMessage(role="user", content=f"message {i}")]
        )
        for i in range(num_sessions)
    ]
    return ChatSessions(session_list=sessions)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_returns_none_when_required_settings_missing():
    """
    If chars-per-token / max-context-tokens / max-output-tokens are not all
    set, validation is not applicable and run() must short-circuit to None
    without ever touching the payload estimator.
    """
    stub = StubPayloadEstimator(tokens=100)
    estimator = ContextWindowEstimator(stub)
    aisp, lp, ep = make_settings(prerequisites_unset=True)

    result = estimator.run(
        chat_sessions=make_chat_sessions(1), aisp=aisp, lp=lp, ep=ep
    )

    assert result is None
    assert stub.calls == []


def test_run_returns_valid_report_within_limit():
    """Total tokens comfortably under the limit -> valid report, no warnings."""
    stub = StubPayloadEstimator(tokens=100)
    estimator = ContextWindowEstimator(stub)
    aisp, lp, ep = make_settings(max_context_tokens=1000, max_output_tokens=200)

    report = estimator.run(
        chat_sessions=make_chat_sessions(2), aisp=aisp, lp=lp, ep=ep
    )

    assert report.is_valid is True
    assert report.max_tokens_limit == 1000
    # 2 sessions * (100 input tokens + 200 reserved output tokens) = 600
    assert report.total_tokens == 600
    assert report.simulation_warnings == []


def test_run_does_not_raise_in_verbose_mode():
    """
    Regression guard for the verbose-gated `debug(...)` call site.

    With verbose=True, run() takes the extra logging branch that used to
    call the undefined `debug(...)`. This must complete normally and return
    a valid report, not raise a NameError-turned-ContextWindowValidatorError.
    """
    stub = StubPayloadEstimator(tokens=100)
    estimator = ContextWindowEstimator(stub)
    aisp, lp, ep = make_settings(
        max_context_tokens=1000, max_output_tokens=200, verbose=True
    )

    report = estimator.run(
        chat_sessions=make_chat_sessions(1), aisp=aisp, lp=lp, ep=ep
    )

    assert report.is_valid is True


def test_run_raises_when_limit_exceeded_and_not_simulating():
    """
    Regression guard for the unconditional `debug(...)` call site.

    Exceeding the limit outside simulation mode must raise a
    ContextWindowValidatorError whose message reflects the actual validation
    failure - never a leaked "name 'debug' is not defined".
    """
    stub = StubPayloadEstimator(
        tokens=900
    )  # 900 input + 200 output = 1100 > 1000 limit
    estimator = ContextWindowEstimator(stub)
    aisp, lp, ep = make_settings(
        max_context_tokens=1000, max_output_tokens=200, simulate=False
    )

    with pytest.raises(ContextWindowValidatorError) as exc_info:
        estimator.run(chat_sessions=make_chat_sessions(1), aisp=aisp, lp=lp, ep=ep)

    message = str(exc_info.value)
    assert "not defined" not in message
    assert "Validation failed" in message


def test_run_collects_warning_instead_of_raising_when_simulating():
    """
    In simulation mode, exceeding the limit must not raise - it should be
    reported as a warning on an is_valid=False report instead, so simulation
    runs never abort just because the payload would be too large.
    """
    stub = StubPayloadEstimator(tokens=900)
    estimator = ContextWindowEstimator(stub)
    aisp, lp, ep = make_settings(
        max_context_tokens=1000, max_output_tokens=200, simulate=True
    )

    report = estimator.run(
        chat_sessions=make_chat_sessions(1), aisp=aisp, lp=lp, ep=ep
    )

    assert report.is_valid is False
    assert len(report.simulation_warnings) == 1
    assert "900" in report.simulation_warnings[0]
    assert "1000" in report.simulation_warnings[0]


def test_run_tracks_high_water_mark_across_multiple_sessions():
    """
    total_tokens, per-session counts, and the high-water mark
    (max_session_tokens / max_session_index) must be computed correctly
    across several sessions of differing size.
    """
    stub = StubPayloadEstimator(tokens=[50, 300, 120])
    estimator = ContextWindowEstimator(stub)
    aisp, lp, ep = make_settings(
        max_context_tokens=10_000, max_output_tokens=100, simulate=True
    )

    report = estimator.run(
        chat_sessions=make_chat_sessions(3), aisp=aisp, lp=lp, ep=ep
    )

    # Per-session totals (input + 100 reserved output tokens each): 150, 400, 220
    assert report.session_token_counts == {0: 150, 1: 400, 2: 220}
    assert report.max_session_index == 1
    assert report.max_session_tokens == 400
    assert report.total_tokens == 150 + 400 + 220


def test_run_wraps_unexpected_estimator_error():
    """
    Any unexpected failure from the injected PayloadEstimator must be caught
    and re-raised as a ContextWindowValidatorError (documenting the module's
    existing broad-except wrapping behaviour), not propagate as a raw,
    unrelated exception type.
    """

    class ExplodingPayloadEstimator:
        def estimate(self, chat_messages, chars_per_token):
            raise RuntimeError("boom")

    estimator = ContextWindowEstimator(ExplodingPayloadEstimator())
    aisp, lp, ep = make_settings()

    with pytest.raises(ContextWindowValidatorError, match="boom"):
        estimator.run(chat_sessions=make_chat_sessions(1), aisp=aisp, lp=lp, ep=ep)
