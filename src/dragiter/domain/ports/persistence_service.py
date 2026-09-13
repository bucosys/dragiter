# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol, runtime_checkable

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession


@runtime_checkable
class PersistenceService(Protocol):
    """Write each successful completion immediately, before the next call."""

    def persist(self, index: int, session: ChatSession, result: ChatResult) -> None:
        """Store *result* for session *index* (1-based). Must not raise to the caller."""
