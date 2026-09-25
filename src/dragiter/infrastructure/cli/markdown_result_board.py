# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dragiter.application.pipeline.material_tokenizer import MaterialTokenizer
from dragiter.domain.models.chat_sessions import ChatSession
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
from dragiter.infrastructure.cli.simulation_brief import (
    SimulationBrief,
    SimulationSessionBrief,
    format_payload_table,
    format_simulation_brief,
    format_simulation_session_brief,
    join_ruled_sections,
    resolve_pack_budget,
)


class MarkdownResultBoard:
    """Markdown result board used on stdout and in -o / -O simulate files."""

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
        chunks = material.chunks
        pack_limit, pack_from = resolve_pack_budget(
            ep.pack_limit_chars_int_setting.is_set,
            ep.pack_limit_chars_int_setting.value,
            self._section_pack_limits(resources, None),
        )
        peak_session = (
            context_report.max_session_index + 1
            if context_report.max_session_index >= 0
            else None
        )
        small_chunks, oversize_chunks = MaterialTokenizer.count_size_flags(
            chunks, pack_limit
        )
        return format_simulation_brief(
            SimulationBrief(
                model=aisp.model_name_string_setting.value or "",
                sessions=session_count,
                chunks=len(chunks),
                valid_chunks=sum(1 for chunk in chunks if chunk.valid),
                source_files=len({chunk.filename for chunk in chunks}),
                loop_items=len(loop.lines),
                total_chars=sum(len(chunk.content) for chunk in chunks),
                sequential=prompt.sequential_processing,
                pack_limit_chars=pack_limit,
                pack_from=pack_from,
                peak_tokens=context_report.max_session_tokens,
                token_limit=context_report.max_tokens_limit,
                peak_session=peak_session,
                window_ok=context_report.is_valid,
                warning_count=len(context_report.simulation_warnings),
                small_chunks=small_chunks,
                oversize_chunks=oversize_chunks,
                output_dir=(
                    str(op.output_directory_path_setting.value)
                    if op.output_directory_path_setting.is_set
                    else None
                ),
                output_file=(
                    str(op.output_file_path_setting.value)
                    if op.output_file_path_setting.is_set
                    else None
                ),
                result_count=result_count,
            ),
            frame=frame,
        )

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
        chunk = chat_session.chunk
        loop_item = chat_session.loop_item or {}
        session_chars: int | None
        if sequential and chunk is not None:
            filename = chunk.filename or "none"
            chunk_label = f"{chunk.num_id} / {max(valid_chunks, 1)}"
            section = chunk.section_name or "none"
            session_chars = len(chunk.content)
            valid_label = "yes" if chunk.valid else "no"
        elif sequential:
            filename = "none"
            chunk_label = "none"
            section = "none"
            session_chars = None
            valid_label = "none"
        else:
            filename = "all files" if valid_chunks else "none"
            chunk_label = "all"
            section = "all"
            session_chars = batched_chars
            valid_label = "yes" if valid_chunks else "no"
        pack_limit_chars, pack_from = resolve_pack_budget(
            ep.pack_limit_chars_int_setting.is_set,
            ep.pack_limit_chars_int_setting.value,
            self._section_pack_limits(resources, chunk if sequential else None),
        )
        if loop_count <= 0:
            loop_label = "none"
            loop_line = "none"
        else:
            loop_num = loop_item.get("LOOP_NUM_ID", session_index)
            loop_label = f"{loop_num} / {loop_count}"
            raw_line = loop_item.get("LOOP_ID") or loop_item.get("LOOP_CONTENT") or ""
            loop_line = " ".join(str(raw_line).split()) or "none"
        tokens = context_report.session_token_counts.get(session_index - 1)
        if tokens is None:
            tokens = context_report.session_input_token_counts.get(session_index - 1)
        return format_simulation_session_brief(
            SimulationSessionBrief(
                session_index=session_index,
                session_count=session_count,
                sequential=sequential,
                filename=filename,
                chunk_label=chunk_label,
                section=section,
                loop_label=loop_label,
                loop_line=loop_line,
                tokens=tokens,
                chars=session_chars,
                pack_limit_chars=pack_limit_chars,
                pack_from=pack_from,
                valid=valid_label,
                loop_items=loop_count,
            )
        )

    def payload_table(self, chat_session: ChatSession) -> str:
        messages = [
            (message.role, message.content)
            for message in chat_session.input_chat_message_list
        ]
        return format_payload_table(messages)

    def join(self, *sections: str) -> str:
        return join_ruled_sections(*sections)

    @staticmethod
    def _section_pack_limits(
        resources: Resources,
        chunk: Chunk | None,
    ) -> list[int | None]:
        sections = resources.resource_sections
        if chunk is not None:
            return [
                section.pack_limit_chars
                for section in sections
                if section.section_name == chunk.section_name
            ]
        return [section.pack_limit_chars for section in sections]
