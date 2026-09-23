# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol, runtime_checkable

from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import OutputParameters
from dragiter.domain.models.prompt_template import PromptTemplate


class OutputCommitError(Exception):
    """Raised when the transfer workspace -> sink fails. The workspace stays in place."""


@runtime_checkable
class OutputCommitService(Protocol):
    """Transfers the persisted completions of a run to the active sink."""

    def commit(
        self,
        op: OutputParameters,
        prompt_template: PromptTemplate,
        sessions: list[ChatSession],
    ) -> None:
        """
        Move or merge the run's persisted completions into the sink and remove
        the run's own workspace on success.

        Raises OutputCommitError on the first failure; the workspace stays.
        """

    def discard(self, op: OutputParameters) -> None:
        """Remove the run's own workspace without committing it (simulate runs)."""
