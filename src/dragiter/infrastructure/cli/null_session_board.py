# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.chat_sessions import ChatSession


class NullSessionBoard:
    """
    Silent SessionBoardService variant for runs without ``-v``.

    Injected explicitly at the composition root; never an implicit fallback
    (ADR-0000, rule 1).
    """

    def begin_run(self, *, model: str, sessions: int, simulate: bool, **facts: object) -> None:
        return None

    def begin_session(self, index: int, total: int, session: ChatSession) -> None:
        return None

    def on_stream_chunk(self) -> None:
        return None

    def abandon_session(self) -> None:
        return None

    def end_session(self, result: ChatResult) -> None:
        return None

    def end_run(self, results: ChatResults) -> None:
        return None
