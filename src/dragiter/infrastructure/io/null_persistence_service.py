# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import OutputParameters
from dragiter.domain.models.prompt_template import PromptTemplate


class NullPersistenceService:
    """
    Discard each result. Test double only.

    Passed in explicitly by tests that opt out of scratch files; never wired in
    production and never used as an implicit fallback (ADR-0000, rules 1 and 8).
    """

    def open(
        self,
        op: OutputParameters,
        prompt_template: PromptTemplate,
        sessions: list[ChatSession],
    ) -> "NullPersistenceService":
        return self

    def persist(self, index: int, session: ChatSession, result: ChatResult) -> None:
        return None
