# =============================================================================
# dragiter - Deterministic RAG Iterator
# Copyright (c) 2026 Michael Buchold <michael.buchold@dragiter.app>
#
# This file is part of dragiter.
#
# dragiter is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dragiter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with dragiter. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing (closed-source use, SaaS, etc.), please contact:
# Michael Buchold <michael.buchold@dragiter.app>
# =============================================================================

import logging

import time
from datetime import datetime, timezone

from dragiter.domain.models.application_result import ApplicationResult
from dragiter.domain.models.chat_results import ChatResults
from dragiter.domain.models.chat_sessions import ChatSessions
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.settings import OutputDirectoryPathSetting, OutputFilePathSetting, OutputModeStringSetting
from typing import Optional, Any

from dragiter.infrastructure.io.io_services import write_or_append_lines_to_unique_file
from dragiter.infrastructure.io.filename_utils import sanitize_filename, ensure_path_within_directory

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

        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)

        return dt.strftime("%Y%m%d_%H%M%S_") + f"{nanoseconds:09d}"


    def _format_filename(
            self,
            chunk: Optional[Chunk] = None,
            loop_dict_item: Optional[dict[str, Any]] = None,
            session_index: Optional[int] = None,
            template: str = ""
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
            d["CHUNK_SECTION_NUM_ID"] = chunk.section_num_id if chunk.section_num_id is not None else 0

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

            d.setdefault("LOOP_ID", sanitize_filename(str(loop_dict_item.get("LOOP_ID", "unknown"))))

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

    def run(self,
            chat_sessions: ChatSessions,
            chat_results: ChatResults,
            output_file_path_setting: OutputFilePathSetting,
            output_directory_path_setting: OutputDirectoryPathSetting,
            output_mode_string_setting: OutputModeStringSetting,
            prompt: PromptTemplate) -> ApplicationResult:

        try:
            open_mode: str = output_mode_string_setting.value or "x"
            application_result = ApplicationResult(0)

            # create simple list
            content_list = []
            for chat_result in chat_results.chat_result_list:
                content_list.append(chat_result.output_chat_message.content)

            # if nothin to report - bail out ...
            out_data = " ".join(content_list)
            if out_data == "": return application_result  # --> out 0

            # printable_value = "\n\n\n\n".join(content_list)
            printable_value = prompt.output_delimiter.join(content_list)
            # write result to one file
            if output_file_path_setting.is_set:
                write_or_append_lines_to_unique_file(output_file_path_setting.value, open_mode, [printable_value])

            # write to many files (all loops, use numbered prompt file name as output filename
            if output_directory_path_setting.is_set:

                #reworking that case

                # generate unique filename

                index: int = 0
                for chat_session, chat_result in zip(chat_sessions.session_list, chat_results.chat_result_list):
                    index += 1
                    chunk: Chunk | None = chat_session.chunk
                    dict_item: dict[str, Any] | None = chat_session.loop_item

                    formatted_file_name: str = self._format_filename(
                        chat_session.chunk,
                        chat_session.loop_item,
                        index,
                        prompt.output_filename_schema)

                    target_path = output_directory_path_setting.value / formatted_file_name
                    # Guarantee the resolved path never leaves the intended output directory
                    safe_path = ensure_path_within_directory(
                        target_path, output_directory_path_setting.value
                    )

                    write_or_append_lines_to_unique_file(
                        safe_path,
                        open_mode, [chat_result.output_chat_message.content])


            print(printable_value)  # to std_out

            return ApplicationResult(0)
        except Exception as e:
            raise OutputWriterError(f"Output dispatcher failure: {e}") from e


class OutputWriterError(Exception):
    pass
