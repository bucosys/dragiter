# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol, runtime_checkable

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import ExecutionParameters, OutputParameters
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

    def persist_prefix(self, content: str) -> None:
        """
        Store *content* as one shard ahead of any session shard, in call order.

        For a once-per-run aggregate artefact only. Callers must never invoke this
        for a sink with a 1:1 shard-to-session requirement (``-O``, STAG Section 7):
        it would make the shard count exceed the session count and abort the commit.
        """

    def reuse(self, index: int) -> bool:
        """
        Report whether session *index* (1-based) already has a shard, and count it.

        ``--resume`` only (STAG Section 5.4/6.4, EXEC-18). ``True`` means the
        caller must skip the LLM call for this session entirely: its shard is
        already in the workspace. Always ``False`` when nothing was adopted.
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
        ep: ExecutionParameters,
    ) -> ResultSink:
        """
        Validate the location, run the early check, create the workspace and
        return the sink for this run.

        With ``ep.resume_bool_setting`` set and ``-O`` active, also adopts the
        newest sibling workspace's shards before returning (STAG Section 5.4).

        Raises PersistenceError (or PersistenceConflictError) before any
        completion call, without leaving a workspace behind.
        """
        ...
