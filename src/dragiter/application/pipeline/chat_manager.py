# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import logging

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.chat_sessions import ChatSessions
from dragiter.domain.models.context_validation_report import ContextValidationReport
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExecutionParameters,
    LoggingParameters,
    OutputParameters,
)
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.resources import Resources
from dragiter.domain.ports.llm_service import LLMService
from dragiter.domain.ports.persistence_service import PersistenceService
from dragiter.domain.ports.session_board_service import SessionBoardService
from dragiter.infrastructure.cli.null_session_board import NullSessionBoard
from dragiter.infrastructure.cli.simulation_brief import resolve_pack_budget
from dragiter.infrastructure.cli.stderr_session_board import StderrSessionBoard
from dragiter.infrastructure.io.scratch_persistence_service import ScratchPersistenceService
from dragiter.infrastructure.llm.mockai_service import MockAIService
from dragiter.infrastructure.llm.simple_payload_estimator import SimplePayloadEstimator

logger = logging.getLogger(__name__)


class ChatManager(Worker):
    def __init__(
        self,
        llm_service: LLMService,
        session_board: SessionBoardService | None = None,
        persistence: PersistenceService | None = None,
    ) -> None:
        self.llm_service = llm_service
        self._session_board = session_board
        self._persistence = persistence

    def run(
        self,
        aisp: AIServiceParameters,
        lp: LoggingParameters,
        ep: ExecutionParameters,
        chat_sessions: ChatSessions,
        op: OutputParameters,
        material: Material,
        loop: Loop,
        context_validation_report: ContextValidationReport,
        resources: Resources,
        prompt_template: PromptTemplate,
    ) -> ChatResults:
        chat_result_list: list[ChatResult] = []
        board = self._resolve_board(lp)
        persistence = self._resolve_persistence(op)
        sessions = chat_sessions.session_list
        total = len(sessions)

        try:
            if ep.simulate_bool_setting.value:
                payload_estimator = SimplePayloadEstimator()
                self.llm_service = MockAIService(payload_estimator)

            board.begin_run(
                model=aisp.model_name_string_setting.value,
                sessions=total,
                simulate=bool(ep.simulate_bool_setting.value),
                **self._board_facts(
                    ep,
                    op,
                    total,
                    material,
                    loop,
                    context_validation_report,
                    resources,
                    prompt_template,
                ),
            )

            for index, session in enumerate(sessions, start=1):
                board.begin_session(index, total, session)
                try:
                    result = self.llm_service.process_query(
                        aisp, lp, session, progress=board
                    )
                except Exception:
                    board.abandon_session()
                    raise
                persistence.persist(index, session, result)
                board.end_session(result)
                chat_result_list.append(result)

            results = ChatResults(chat_result_list)
            board.end_run(results)
            return results

        except Exception as e:
            raise ChatManagerError(f"Failed to process openai query: {e}") from e

    def _resolve_board(self, lp: LoggingParameters) -> SessionBoardService:
        if self._session_board is not None:
            return self._session_board
        if lp.verbose_bool_setting.value:
            return StderrSessionBoard()
        return NullSessionBoard()

    @staticmethod
    def _board_facts(
        ep: ExecutionParameters,
        op: OutputParameters,
        sessions: int,
        material: Material,
        loop: Loop,
        report: ContextValidationReport,
        resources: Resources,
        prompt_template: PromptTemplate,
    ) -> dict[str, object]:
        chunks = material.chunks
        section_limits = [
            section.pack_limit_chars
            for section in resources.resource_sections
        ]
        pack_limit, pack_from = resolve_pack_budget(
            ep.pack_limit_chars_int_setting.is_set,
            ep.pack_limit_chars_int_setting.value,
            section_limits,
        )
        output = "none"
        if op.output_directory_path_setting.is_set:
            output = str(op.output_directory_path_setting.value)
        elif op.output_file_path_setting.is_set:
            output = str(op.output_file_path_setting.value)
        peak_session = None
        if report.max_session_index >= 0:
            peak_session = report.max_session_index + 1
        window_applicable = report.max_tokens_limit > 0
        return {
            "sequential": bool(prompt_template.sequential_processing),
            "chunks": len(chunks),
            "source_files": len({chunk.filename for chunk in chunks}),
            "valid_chunks": sum(1 for chunk in chunks if chunk.valid),
            "loop_items": len(loop.lines),
            "total_chars": sum(len(chunk.content) for chunk in chunks),
            "pack_limit_chars": pack_limit,
            "pack_from": pack_from,
            "window_ok": report.is_valid if window_applicable else None,
            "peak_tokens": report.max_session_tokens if window_applicable else None,
            "token_limit": report.max_tokens_limit if window_applicable else None,
            "peak_session": peak_session if window_applicable else None,
            "warning_count": len(report.simulation_warnings),
            "output": output,
            "planned_sessions": sessions,
        }

    def _resolve_persistence(self, op: OutputParameters) -> PersistenceService:
        if self._persistence is not None:
            return self._persistence
        return ScratchPersistenceService.from_output_parameters(op)


class ChatManagerError(Exception):
    pass
