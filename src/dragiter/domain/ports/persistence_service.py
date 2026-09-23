# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol, runtime_checkable

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import OutputParameters
from dragiter.domain.models.prompt_template import PromptTemplate


class PersistenceError(Exception):
    """Raised when the run workspace cannot be set up or a completion cannot be persisted."""


class PersistenceConflictError(PersistenceError):
    """Raised by ``PersistenceService.open`` when the planned run would violate the output mode."""


@runtime_checkable
class ResultSink(Protocol):
    """Run-scoped target for completions, obtained from ``PersistenceService.open``."""

    def persist(self, index: int, session: ChatSession, result: ChatResult) -> None:
        """
        Store *result* for session *index* (1-based) as one finished shard.

        Raises PersistenceError if the shard cannot be written; the run aborts.
        """


@runtime_checkable
class PersistenceService(Protocol):
    """
    Write each completion immediately, before the next call.

    The service is constructed at the composition root without run data. Everything
    that only exists once the pipeline has run (output settings, prompt template,
    planned sessions) is handed over in ``open``.
    """

    def open(
        self,
        op: OutputParameters,
        prompt_template: PromptTemplate,
        sessions: list[ChatSession],
    ) -> ResultSink:
        """
        Validate the location, run the early check, create the workspace and
        return the sink for this run.

        Raises PersistenceError (or PersistenceConflictError) before any
        completion call, without leaving a workspace behind.
        """
        ...
