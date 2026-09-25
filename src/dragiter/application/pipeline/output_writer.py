# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold
import logging

from dragiter.domain.models.application_result import ApplicationResult
from dragiter.domain.models.chat_sessions import ChatSessions
from dragiter.domain.models.parameters import OutputParameters
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.ports.output_commit_service import OutputCommitService

logger = logging.getLogger(__name__)


class OutputWriter:
    """
    Final pipeline step: commits the run workspace to its sink (STAG Section 7).

    Live and simulate runs are committed identically — ChatManager already
    persisted the right content (real replies, or a simulate session's board and
    complete outgoing request) as shards; this class does not distinguish them.
    """

    def __init__(self, output_commit: OutputCommitService) -> None:
        self._commit = output_commit

    def run(
        self,
        chat_sessions: ChatSessions,
        op: OutputParameters,
        prompt: PromptTemplate,
    ) -> ApplicationResult:
        try:
            self._commit.commit(op, prompt, chat_sessions.session_list)
            return ApplicationResult(0)
        except Exception as e:
            # Translate I/O error into a domain-specific error
            raise OutputWriterError(f"Output commit failure: {e}") from e


class OutputWriterError(Exception):
    pass
