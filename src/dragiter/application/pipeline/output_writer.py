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
from dragiter.domain.ports.result_board_service import ResultBoardService
from dragiter.infrastructure.cli.markdown_result_board import MarkdownResultBoard
from dragiter.infrastructure.io.filename_utils import (
    ensure_path_within_directory,
    format_output_filename,
)
from dragiter.infrastructure.io.workspace_service import (
    cleanup_run_workspaces,
    commit_assembled_output,
    join_workspace_text,
    list_workspace_files,
)

logger = logging.getLogger(__name__)


class OutputWriter:
    def __init__(self, result_board: ResultBoardService) -> None:
        self._board = result_board

    def _format_filename(
        self,
        chunk: Chunk | None = None,
        loop_dict_item: dict[str, Any] | None = None,
        session_index: int | None = None,
        template: str = "",
    ) -> str:
        return format_output_filename(
            chunk, loop_dict_item, session_index, template
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
            open_mode: str = op.output_mode_string_setting.value or "x"
            application_result = ApplicationResult(0)

            # create simple list
            content_list = []
            for chat_result in chat_results.chat_result_list:
                content_list.append(chat_result.output_chat_message.content)

            out_data = " ".join(content_list)
            if out_data == "" and not list_workspace_files(op):
                cleanup_run_workspaces(op)
                return application_result

            # printable_value = "\n\n\n\n".join(content_list)
            printable_value = prompt.output_delimiter.join(content_list)
            simulate = self._is_simulation(ep, chat_results)
            run_board_tty = (
                self._board.run_board(
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
                    frame=True,
                )
                if simulate
                else None
            )
            run_board_file = (
                self._board.run_board(
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
                    frame=False,
                )
                if simulate
                else None
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

            delimiter = prompt.output_delimiter or ""
            staged_files = list_workspace_files(op)
            staged_join = join_workspace_text(op, delimiter) if staged_files else None

            # write result to one file (-o)
            if op.output_file_path_setting.is_set:
                if simulate and run_board_file is not None:
                    sections = [run_board_file]
                    for index, (session, result) in enumerate(
                        zip(
                            chat_sessions.session_list,
                            chat_results.chat_result_list,
                            strict=True,
                        ),
                        start=1,
                    ):
                        sections.append(_session_header(index, session))
                        sections.append(self._board.payload_table(session))
                    file_body = self._board.join(*sections)
                elif staged_join is not None:
                    file_body = staged_join
                else:
                    file_body = printable_value
                commit_assembled_output(
                    Path(op.output_file_path_setting.value),
                    open_mode,
                    file_body,
                    delimiter,
                )

            # write to many files (-O)
            if op.output_directory_path_setting.is_set:
                file_mappings = []
                target_dir = Path(op.output_directory_path_setting.value)
                if simulate:
                    for index, (chat_session, chat_result) in enumerate(
                        zip(
                            chat_sessions.session_list,
                            chat_results.chat_result_list,
                            strict=True,
                        ),
                        start=1,
                    ):
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
                        file_mappings.append((safe_path, body))
                elif staged_files:
                    sessions = chat_sessions.session_list
                    for index, staged in enumerate(staged_files, start=1):
                        body = staged.read_text(encoding="utf-8")
                        if index <= len(sessions):
                            session = sessions[index - 1]
                            formatted_file_name = self._format_filename(
                                session.chunk,
                                session.loop_item,
                                index,
                                prompt.output_filename_schema,
                            )
                        else:
                            formatted_file_name = staged.name
                        safe_path = ensure_path_within_directory(
                            target_dir / formatted_file_name, target_dir
                        )
                        file_mappings.append((safe_path, body))
                else:
                    for index, (chat_session, chat_result) in enumerate(
                        zip(
                            chat_sessions.session_list,
                            chat_results.chat_result_list,
                            strict=True,
                        ),
                        start=1,
                    ):
                        formatted_file_name = self._format_filename(
                            chat_session.chunk,
                            chat_session.loop_item,
                            index,
                            prompt.output_filename_schema,
                        )
                        safe_path = ensure_path_within_directory(
                            target_dir / formatted_file_name, target_dir
                        )
                        file_mappings.append(
                            (safe_path, chat_result.output_chat_message.content or "")
                        )

                for safe_path, body in file_mappings:
                    commit_assembled_output(
                        safe_path,
                        open_mode,
                        body,
                        delimiter,
                        allow_empty=True,
                    )

            # Default sink is stdout only when neither -o nor -O is set.
            if self._echo_results_to_stdout(op):
                if run_board_tty is not None:
                    print(run_board_tty)
                elif staged_join is not None:
                    print(staged_join)
                else:
                    print(printable_value)
            cleanup_run_workspaces(op)
            return ApplicationResult(0)

        except Exception as e:
            # Translate I/O error into a domain-specific error
            raise OutputWriterError(f"Output dispatcher failure: {e}") from e

    @staticmethod
    def _echo_results_to_stdout(op: OutputParameters) -> bool:
        """Return True when assembled output should also be printed on stdout.

        Stdout is the default sink. Once ``output_file`` (``-o``) or
        ``output_directory`` (``-O``) is set from any configuration source,
        file routing replaces that sink.

        Redirection of stdout (``>``, ``>>``, ``|``) is not inspected.
        ``isatty()`` cannot tell a user pipe from CI or test capture, and
        treating a redirected stream as an extra sink would duplicate the
        file output the caller already asked for.
        """
        return not (
            op.output_file_path_setting.is_set
            or op.output_directory_path_setting.is_set
        )

    @staticmethod
    def _is_simulation(ep: ExecutionParameters, chat_results: ChatResults) -> bool:
        if bool(ep.simulate_bool_setting.value):
            return True
        return any(result.finish_reason == "mock" for result in chat_results.chat_result_list)


class OutputWriterError(Exception):
    pass
