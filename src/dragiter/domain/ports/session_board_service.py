# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol, runtime_checkable

from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.ports.stream_progress_listener import StreamProgressListener


@runtime_checkable
class SessionBoardService(StreamProgressListener, Protocol):
    """stderr run board: start block, one request line, closing block."""

    def begin_run(self, *, model: str, sessions: int, simulate: bool, **facts: object) -> None:
        """Write the opening board (every line prefixed)."""

    def begin_session(self, index: int, total: int, session: ChatSession) -> None:
        """Open the live request line for session *index* of *total*."""

    def end_session(self, result: ChatResult) -> None:
        """Finish the request line with duration and token counts."""

    def end_run(self, results: ChatResults) -> None:
        """Write the closing board (every line prefixed)."""
