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
from dragiter.domain.ports.persistence_service import (
    PersistenceError,
    PersistenceService,
)
from dragiter.domain.ports.session_board_service import SessionBoardService
from dragiter.infrastructure.cli.simulation_brief import resolve_pack_budget

logger = logging.getLogger(__name__)


class ChatManager(Worker):
    """
    Runs every chat session against the LLM service selected for this run.

    All collaborators are constructed at the composition root without run data.
    Run data (parameters, prompt template, sessions) is handed to them per call;
    none of them is replaced or reassigned afterwards (ADR-0000, rule 6).
    """

    def __init__(
        self,
        llm_service: LLMService,
        mock_service: LLMService,
        verbose_board: SessionBoardService,
        silent_board: SessionBoardService,
        persistence: PersistenceService,
    ) -> None:
        # Validate, never substitute (ADR-0000, rule 3). The Protocol check only
        # verifies method names (rule 13); signatures are covered by mypy.
        _require(llm_service, LLMService, "llm_service")
        _require(mock_service, LLMService, "mock_service")
        _require(verbose_board, SessionBoardService, "verbose_board")
        _require(silent_board, SessionBoardService, "silent_board")
        _require(persistence, PersistenceService, "persistence")
        self._llm_service: LLMService = llm_service
        self._mock_service: LLMService = mock_service
        self._verbose_board: SessionBoardService = verbose_board
        self._silent_board: SessionBoardService = silent_board
        self._persistence: PersistenceService = persistence

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
        simulate = bool(ep.simulate_bool_setting.value)
        verbose = bool(lp.verbose_bool_setting.value)
        # All variants were injected; the run parameters only pick among them.
        # Nothing is reassigned, so the manager behaves the same on every run.
        llm_service = self._mock_service if simulate else self._llm_service
        board = self._verbose_board if verbose else self._silent_board
        sessions = chat_sessions.session_list
        total = len(sessions)

        try:
            sink = self._persistence.open(op, prompt_template, sessions)

            board.begin_run(
                model=aisp.model_name_string_setting.value,
                sessions=total,
                simulate=simulate,
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
                    result = llm_service.process_query(aisp, lp, session, progress=board)
                except Exception:
                    board.abandon_session()
                    raise
                sink.persist(index, session, result)
                board.end_session(result)
                chat_result_list.append(result)

            results = ChatResults(chat_result_list)
            board.end_run(results)
            return results

        except PersistenceError as e:
            raise ChatManagerError(str(e)) from e
        except Exception as e:
            raise ChatManagerError(f"Failed to process chat session: {e}") from e

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
        if (
            report.max_tokens_limit is not None
            and report.max_session_index >= 0
        ):
            peak_session = report.max_session_index + 1
        return {
            "sequential": bool(prompt_template.sequential_processing),
            "chunks": len(chunks),
            "source_files": len({chunk.filename for chunk in chunks}),
            "valid_chunks": sum(1 for chunk in chunks if chunk.valid),
            "loop_items": len(loop.lines),
            "total_chars": sum(len(chunk.content) for chunk in chunks),
            "pack_limit_chars": pack_limit,
            "pack_from": pack_from,
            "window_ok": report.is_valid,
            "peak_tokens": report.max_session_tokens,
            "token_limit": report.max_tokens_limit,
            "peak_session": peak_session,
            "warning_count": len(report.simulation_warnings),
            "output": output,
            "planned_sessions": sessions,
        }


def _require(value: object, protocol: type, name: str) -> None:
    if not isinstance(value, protocol):
        raise TypeError(
            f"ChatManager: '{name}' must implement {protocol.__name__}, "
            f"got {type(value).__name__}."
        )


class ChatManagerError(Exception):
    pass
