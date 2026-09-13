# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession


class NullPersistenceService:
    """Discard each result. Used only in tests that opt out of scratch files."""

    def persist(self, index: int, session: ChatSession, result: ChatResult) -> None:
        return None
