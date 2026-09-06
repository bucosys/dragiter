# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold
from datetime import UTC, datetime
import logging
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any

from dragiter.domain.models.application_result import ApplicationResult
from dragiter.domain.models.chat_results import ChatResults
from dragiter.domain.models.chat_sessions import ChatSessions
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.parameters import OutputParameters
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.infrastructure.io.filename_utils import (
    ensure_path_within_directory,
    sanitize_filename,
)
from dragiter.infrastructure.io.io_services import (
    write_directory_with_staging,
    write_or_append_lines_to_unique_file,
)

logger = logging.getLogger(__name__)


class OutputWriter:
    def __init__(self) -> None:
        pass

    def _get_sortable_timestamp(self) -> str:
        """
        Generates a high-resolution, sortable timestamp string.

        The format is designed to be lexicographically sortable and
        includes nanosecond precision.

        Returns:
            str: Timestamp in the format 'YYYYMMDD_HHMMSS_nnnnnnnnn'
                 Example: '20250621_231845_847291384'
        """
        ns = time.time_ns()

        # Separate seconds and nanoseconds
        seconds = ns // 1_000_000_000
        nanoseconds = ns % 1_000_000_000

        dt = datetime.fromtimestamp(seconds, tz=UTC)

        return dt.strftime("%Y%m%d_%H%M%S_") + f"{nanoseconds:09d}"

    def _format_filename(
        self,
        chunk: Chunk | None = None,
        loop_dict_item: dict[str, Any] | None = None,
        session_index: int | None = None,
        template: str = "",
    ) -> str:
        """
        Formats a filename using the provided template.
        Ensures numeric format specifiers work correctly.
        """
        result = template or ""
        d: dict[str, Any] = {}

        # Chunk data
        if chunk:
            d["CHUNK_NUM_ID"] = chunk.num_id if chunk.num_id is not None else 0
            d["CHUNK_FILE_NAME"] = sanitize_filename(chunk.filename or "file")
            d["CHUNK_SECTION_NAME"] = sanitize_filename(chunk.section_name or "section")
            d["CHUNK_SECTION_NUM_ID"] = (
                chunk.section_num_id if chunk.section_num_id is not None else 0
            )

        # Loop data - force numeric fields to int
        if loop_dict_item:
            for key, value in loop_dict_item.items():
                if key.endswith("_NUM_ID") or key == "LOOP_NUM_ID":
                    try:
                        d[key] = int(value)
                    except (ValueError, TypeError):
                        d[key] = session_index or 0
                elif isinstance(value, (int, float)):
                    d[key] = value
                else:
                    d[key] = sanitize_filename(str(value))

            # Ensure LOOP_NUM_ID is always present and numeric
            if "LOOP_NUM_ID" not in d:
                d["LOOP_NUM_ID"] = session_index or 0

            d.setdefault(
                "LOOP_ID",
                sanitize_filename(str(loop_dict_item.get("LOOP_ID", "unknown"))),
            )

        # Timestamp
        d["TIMESTAMP"] = self._get_sortable_timestamp()

        # Fallback if no placeholders
        known_placeholders = ["CHUNK_", "LOOP_", "TIMESTAMP"]
        if not any(ph in result for ph in known_placeholders):
            if session_index is not None:
                return f"session_{session_index:04d}.md"
            return "output.md"

        try:
            formatted = result.format_map(d)
        except (KeyError, ValueError):
            if session_index is not None:
                return f"session_{session_index:04d}.md"
            formatted = result

        return sanitize_filename(formatted)

    def _write_to_directory_with_staging(
        self,
        chat_sessions: ChatSessions,
        chat_results: ChatResults,
        final_dir: Path,
        prompt: PromptTemplate,
        open_mode: str,
    ) -> None:
        """Writes results to a temporary staging directory first and transfers them upon completion."""

        # 1. Generate staging directory (in the OS temp directory)
        #staging_dir = Path(tempfile.mkdtemp(prefix="dragiter_staging_"))
        staging_dir = final_dir / f".tmp_staging_{os.getpid()}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        try:
            # List for the subsequent commit phase
            file_mappings = []
            index: int = 0

            # 2. Write LLM results to the staging directory
            for chat_session, chat_result in zip(
                chat_sessions.session_list,
                chat_results.chat_result_list,
                strict=True,
            ):
                index += 1
                formatted_file_name: str = self._format_filename(
                    chat_session.chunk,
                    chat_session.loop_item,
                    index,
                    prompt.output_filename_schema,
                )

                content = chat_result.output_chat_message.content
                staged_path = staging_dir / formatted_file_name

                # Write to the staging directory without conflicts (always mode "x")
                write_or_append_lines_to_unique_file(staged_path, "x", [content])

                # Prepare target data for the commit phase
                target_path = final_dir / formatted_file_name
                safe_path = ensure_path_within_directory(target_path, final_dir)
                file_mappings.append((safe_path, content))

            # 3. Commit phase: Transfer to the actual target directory
            for safe_path, content in file_mappings:
                try:
                    write_or_append_lines_to_unique_file(safe_path, open_mode, [content])
                except Exception as e:
                    # If writing to the final target fails (e.g., due to mode "x"):
                    raise OutputWriterError(
                        f"Write conflict for file {safe_path.name}. "
                        f"Aborting! All generated results are safely stored in: {staging_dir}\n"
                        f"Original error: {e}"
                    ) from e

            # 4. Cleanup: Remove the staging directory if successful
            shutil.rmtree(staging_dir, ignore_errors=True)

        except Exception as e:
            # Pass through if it is our own OutputWriterError
            if isinstance(e, OutputWriterError):
                raise
            # Otherwise catch and point to the staging directory
            raise OutputWriterError(
                f"Unexpected error. The temporary data is stored in: {staging_dir} | {e}"
            ) from e

    def run(
        self,
        chat_sessions: ChatSessions,
        chat_results: ChatResults,
        op: OutputParameters,
        prompt: PromptTemplate,
    ) -> ApplicationResult:

        try:
            open_mode: str = op.output_mode_string_setting.value or "x"
            application_result = ApplicationResult(0)

            # create simple list
            content_list = []
            for chat_result in chat_results.chat_result_list:
                content_list.append(chat_result.output_chat_message.content)

            # if nothin to report - bail out ...
            out_data = " ".join(content_list)
            if out_data == "":
                return application_result  # --> out 0

            # printable_value = "\n\n\n\n".join(content_list)
            printable_value = prompt.output_delimiter.join(content_list)
            # write result to one file
            if op.output_file_path_setting.is_set:
                write_or_append_lines_to_unique_file(
                    op.output_file_path_setting.value, open_mode, [printable_value]
                )

            # write to many files (-O) -> Utilises the new staging method
            if op.output_directory_path_setting.is_set:
                file_mappings = []
                index: int = 0

                for chat_session, chat_result in zip(
                        chat_sessions.session_list,
                        chat_results.chat_result_list,
                        strict=True,
                ):
                    index += 1
                    formatted_file_name: str = self._format_filename(
                        chat_session.chunk,
                        chat_session.loop_item,
                        index,
                        prompt.output_filename_schema,
                    )
                    target_path = op.output_directory_path_setting.value / formatted_file_name
                    safe_path = ensure_path_within_directory(
                        target_path, op.output_directory_path_setting.value
                    )
                    file_mappings.append((safe_path, chat_result.output_chat_message.content))

                # Delegate the complete transfer to the infrastructure layer
                write_directory_with_staging(
                    file_mappings=file_mappings,
                    target_dir=op.output_directory_path_setting.value,
                    output_mode=open_mode
                )

            # last step - print to stdout
            print(printable_value)  # to std_out
            return ApplicationResult(0)

        except Exception as e:
            # Translate I/O error into a domain-specific error
            raise OutputWriterError(f"Output dispatcher failure: {e}") from e


class OutputWriterError(Exception):
    pass



