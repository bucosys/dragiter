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
# Runtime collaborators for the OpenAI-compatible streaming adapter:
# transport construction and completion retry policy.
# =============================================================================

from __future__ import annotations

import logging
import socket
import ssl
from typing import Any

import httpx2
import openai
from openai import DefaultHttpx2Client

from dragiter.domain.models.parameters import AIServiceParameters

logger = logging.getLogger(__name__)


class CompletionRetryPolicy:
    """Owns retry count, wait and the decision which faults are worth repeating.

    504 / stream-timeout and an Ollama runner crash are treated as terminal:
    repeating the same heavy prompt behind a short gateway idle limit only
    piles more work onto a dying worker.
    """

    def max_attempts(self, aisp: AIServiceParameters) -> int:
        setting = aisp.max_retries_int_setting
        if setting.is_set and setting.value is not None:
            return max(1, int(setting.value))
        return 1

    def wait_seconds(self, attempt: int, retry_delay: int) -> int:
        """Backoff before *attempt* (1-based). Attempt 1 never waits."""
        if attempt <= 1:
            return 0
        return retry_delay * (2 ** (attempt - 2))

    def is_retryable(self, exc: BaseException) -> bool:
        if self.is_gateway_timeout(exc) or self.is_runner_crash(exc):
            return False
        if isinstance(exc, openai.RateLimitError):
            return True
        if isinstance(exc, openai.APITimeoutError):
            return False
        return isinstance(exc, openai.APIConnectionError)

    def describe(self, exc: BaseException) -> str:
        status = self.http_status(exc)
        if self.is_gateway_timeout(exc):
            return (
                f"proxy/gateway timeout before the first stream token "
                f"(HTTP {status or 504}). The upstream likely exceeded the "
                f"gateway idle limit (often 60 s). Retrying the same prompt "
                f"will not help; shrink the payload or raise the proxy timeout."
            )
        if self.is_runner_crash(exc):
            return (
                "the model runner stopped (Ollama resource limit or internal "
                "crash). Further retries would pile more load onto a dead worker."
            )
        if status is not None:
            return f"HTTP {status}: {exc}"
        return str(exc)

    @staticmethod
    def http_status(exc: BaseException) -> int | None:
        status = getattr(exc, "status_code", None)
        return status if isinstance(status, int) else None

    def is_gateway_timeout(self, exc: BaseException) -> bool:
        if self.http_status(exc) == 504:
            return True
        text = str(exc).lower()
        return "gateway timeout" in text or "stream timeout" in text

    @staticmethod
    def is_runner_crash(exc: BaseException) -> bool:
        return "model runner has unexpectedly stopped" in str(exc).lower()


class OpenAITransportFactory:
    """Build the httpx2 client (TLS / mTLS / keepalive / timeouts)."""

    def create(self, aisp: AIServiceParameters) -> DefaultHttpx2Client:
        verify: bool | str | ssl.SSLContext = True
        cert = None
        ca_path: str | None = None

        if aisp.ca_bundle_file_path_setting.is_set:
            ca_path = str(aisp.ca_bundle_file_path_setting.value)
            logger.debug(f"Using custom CA bundle: {ca_path}")
            verify = ca_path

        if aisp.client_cert_file_path_setting.is_set:
            cert_path = str(aisp.client_cert_file_path_setting.value)
            if aisp.client_key_file_path_setting.is_set:
                key_path = str(aisp.client_key_file_path_setting.value)
                logger.debug("mTLS: Using client cert + separate key")
                ctx = ssl.create_default_context(cafile=ca_path)
                ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
                verify = ctx
                cert = None
            else:
                cert = cert_path
                logger.debug("mTLS: Using combined client cert file")

        transport_kwargs: dict[str, Any] = {}
        if aisp.tcp_keep_alive_bool_setting.value:
            try:
                transport_kwargs["socket_options"] = self._keepalive_socket_options()
                logger.debug("TCP Keepalive enabled")
            except Exception as e:
                logger.warning(f"Could not enable TCP Keepalive: {e}")

        transport = httpx2.HTTPTransport(**transport_kwargs) if transport_kwargs else None
        timeout = httpx2.Timeout(connect=30.0, read=None, write=60.0, pool=30.0)

        if transport is not None:
            return DefaultHttpx2Client(
                verify=verify,
                cert=cert,
                transport=transport,
                timeout=timeout,
            )
        return DefaultHttpx2Client(verify=verify, cert=cert, timeout=timeout)

    @staticmethod
    def _keepalive_socket_options() -> list[tuple[int, int, int]]:
        options: list[tuple[int, int, int]] = [
            (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
        ]
        if hasattr(socket, "TCP_KEEPIDLE"):
            options.append((socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30))
            options.append((socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10))
            options.append((socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3))
        elif hasattr(socket, "TCP_KEEPALIVE"):
            options.append((socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, 30))
        return options
