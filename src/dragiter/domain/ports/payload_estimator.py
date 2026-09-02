# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol

from dragiter.domain.models.chat_sessions import ChatMessage


class PayloadEstimator(Protocol):
    """
    Structural interface for payload token estimation.
    """

    def estimate(
        self, chat_messages: list[ChatMessage], chars_per_token: float
    ) -> int: ...


class PayloadEstimatorError(Exception):
    pass
