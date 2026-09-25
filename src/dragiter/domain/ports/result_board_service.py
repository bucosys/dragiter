# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol, runtime_checkable

from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.context_validation_report import ContextValidationReport
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExecutionParameters,
    OutputParameters,
)
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.resources import Resources


@runtime_checkable
class ResultBoardService(Protocol):
    """Assemble the post-run result board (stdout or file), not the live stderr board."""

    def run_board(
        self,
        session_count: int,
        result_count: int,
        op: OutputParameters,
        ep: ExecutionParameters,
        aisp: AIServiceParameters,
        material: Material,
        loop: Loop,
        context_report: ContextValidationReport,
        prompt: PromptTemplate,
        resources: Resources,
        *,
        frame: bool = True,
    ) -> str:
        """Render the run-level board. Built from counts, not live objects, so it
        can be assembled before every session has actually run (ChatManager builds
        it once, ahead of the session loop, for a simulate run's leading shard)."""

    def session_board(
        self,
        chat_session: ChatSession,
        session_index: int,
        session_count: int,
        sequential: bool,
        valid_chunks: int,
        loop_count: int,
        context_report: ContextValidationReport,
        batched_chars: int,
        ep: ExecutionParameters,
        resources: Resources,
    ) -> str:
        """Render the per-session board."""

    def payload_table(self, chat_session: ChatSession) -> str:
        """Render the role/content table for one assembled request."""

    def join(self, *sections: str) -> str:
        """Join ruled sections in the file-board layout."""
