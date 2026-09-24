# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold
import logging
from pathlib import Path
from typing import Any

from dragiter.domain.models.application_result import ApplicationResult
from dragiter.domain.models.chat_results import ChatResults
from dragiter.domain.models.chat_sessions import ChatSession, ChatSessions
from dragiter.domain.models.chunk import Chunk
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
from dragiter.domain.ports.output_commit_service import OutputCommitService
from dragiter.domain.ports.result_board_service import ResultBoardService
from dragiter.infrastructure.io.filename_utils import (
    ensure_path_within_directory,
    format_output_filename,
    sortable_timestamp,
)
from dragiter.infrastructure.io.workspace_service import commit_assembled_output

logger = logging.getLogger(__name__)


class OutputWriter:
    """
    Final pipeline step.

    Live runs: the persisted completions are committed from the run workspace
    (STAG Section 7) by the injected OutputCommitService.
    Simulate runs: the result boards are written instead and the workspace is
    discarded (simulate boards are outside the staging profile, STAG Section 2.2).
    """

    def __init__(
        self,
        result_board: ResultBoardService,
        output_commit: OutputCommitService,
    ) -> None:
        self._board = result_board
        self._commit = output_commit

    def _format_filename(
        self,
        chunk: Chunk | None = None,
        loop_dict_item: dict[str, Any] | None = None,
        session_index: int | None = None,
        template: str = "",
    ) -> str:
        # Simulate boards have no shard; the clock at write time is their timestamp.
        return format_output_filename(
            chunk, loop_dict_item, session_index, template, timestamp=sortable_timestamp()
        )

    def run(
        self,
        chat_sessions: ChatSessions,
        chat_results: ChatResults,
        op: OutputParameters,
        prompt: PromptTemplate,
        ep: ExecutionParameters,
        aisp: AIServiceParameters,
        material: Material,
        loop: Loop,
        context_report: ContextValidationReport = None,
        resources: Resources = None,
    ) -> ApplicationResult:
        try:
            if not self._is_simulation(ep, chat_results):
                self._commit.commit(op, prompt, chat_sessions.session_list)
                return ApplicationResult(0)

            self._write_simulation(
                chat_sessions,
                chat_results,
                op,
                prompt,
                ep,
                aisp,
                material,
                loop,
                context_report,
                resources,
            )
            self._commit.discard(op)
            return ApplicationResult(0)

        except Exception as e:
            # Translate I/O error into a domain-specific error
            raise OutputWriterError(f"Output dispatcher failure: {e}") from e

    def _write_simulation(
        self,
        chat_sessions: ChatSessions,
        chat_results: ChatResults,
        op: OutputParameters,
        prompt: PromptTemplate,
        ep: ExecutionParameters,
        aisp: AIServiceParameters,
        material: Material,
        loop: Loop,
        context_report: ContextValidationReport | None,
        resources: Resources | None,
    ) -> None:
        open_mode: str = op.output_mode_string_setting.value
        delimiter = prompt.output_delimiter or ""

        def _run_board(frame: bool) -> str:
            return self._board.run_board(
                chat_sessions,
                chat_results,
                op,
                ep,
                aisp,
                material,
                loop,
                context_report,
                prompt,
                resources,
                frame=frame,
            )

        session_count = len(chat_sessions.session_list)
        valid_chunks = sum(1 for chunk in material.chunks if chunk.valid)
        loop_count = len(loop.lines)
        batched_chars = sum(len(chunk.content) for chunk in material.chunks if chunk.valid)

        def _session_header(index: int, chat_session: ChatSession) -> str:
            return self._board.session_board(
                chat_session,
                index,
                session_count,
                prompt.sequential_processing,
                valid_chunks,
                loop_count,
                context_report,
                batched_chars,
                ep,
                resources,
            )

        # -o: one file with the run board and every session board
        if op.output_file_path_setting.is_set:
            sections = [_run_board(frame=False)]
            for index, session in enumerate(chat_sessions.session_list, start=1):
                sections.append(_session_header(index, session))
                sections.append(self._board.payload_table(session))
            commit_assembled_output(
                Path(op.output_file_path_setting.value),
                open_mode,
                self._board.join(*sections),
                delimiter,
            )
            return

        # -O: one board file per session
        if op.output_directory_path_setting.is_set:
            target_dir = Path(op.output_directory_path_setting.value)
            for index, chat_session in enumerate(chat_sessions.session_list, start=1):
                formatted_file_name = self._format_filename(
                    chat_session.chunk,
                    chat_session.loop_item,
                    index,
                    prompt.output_filename_schema,
                )
                safe_path = ensure_path_within_directory(
                    target_dir / formatted_file_name, target_dir
                )
                body = self._board.join(
                    _session_header(index, chat_session),
                    self._board.payload_table(chat_session),
                )
                commit_assembled_output(
                    safe_path, open_mode, body, delimiter, allow_empty=True
                )
            return

        # stdout-only
        print(_run_board(frame=True))

    @staticmethod
    def _is_simulation(ep: ExecutionParameters, chat_results: ChatResults) -> bool:
        if bool(ep.simulate_bool_setting.value):
            return True
        return any(result.finish_reason == "mock" for result in chat_results.chat_result_list)


class OutputWriterError(Exception):
    pass
