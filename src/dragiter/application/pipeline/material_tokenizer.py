# =============================================================================
# dragiter - Deterministic Context Iterator
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
import re

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.material import Material, Chunk
from dragiter.domain.models.resources import Resources, ResourceSection
from dragiter.domain.ports.text_file_reader import TextFileReader

logger = logging.getLogger(__name__)


class MaterialTokenizer(Worker):
    def __init__(self, text_file_reader: TextFileReader) -> None:
        self.text_file_reader = text_file_reader

    def run(self, resources: Resources) -> Material:
        all_chunks: list[Chunk] = []

        try:
            for resource_section in resources.resource_sections:
                all_chunks.extend(self._process_markdown_configs(resource_section))

            return Material(chunks=all_chunks)

        except Exception as e:
            raise MaterialTokenizerError(f"Failed to create chunks.") from e

    def _process_markdown_configs(self, rs: ResourceSection) -> list[Chunk]:
        section_chunks: list[Chunk] = []
        global_id: int = 1

        for path_obj in rs.file_paths:
            content = self.text_file_reader.read(path_obj)  # INHERITANCE TEXT_FILE SAVE READ FILE CONTENT ###
            section_internal_id = 1

            # Split content using the regex.
            # Capturing groups in regex ensure headers are kept in the 'parts' list.
            parts = re.split(rs.regex_pattern, content, flags=re.MULTILINE)

            # 1. HANDLE PREAMBLE OR FULL TEXT IF NO MATCH
            # parts[0] contains everything before the first match.
            # If no matches are found, parts[0] contains the entire file content.
            preamble = parts[0].strip()
            if preamble:
                section_chunks.append(Chunk(
                    num_id=global_id,
                    filename=path_obj.path.as_posix(),
                    section_name=rs.section_name,
                    section_num_id=section_internal_id,
                    valid=self._is_content_valid(preamble, rs.exclude_filters, rs._include_filters),
                    content=preamble
                ))
                global_id += 1
                section_internal_id += 1

            # 2. HANDLE MATCHED CHAPTERS
            # If regex matched, parts will have odd indices (1, 3, 5...) as headers
            # and even indices (2, 4, 6...) as the corresponding body text.
            for i in range(1, len(parts), 2):
                header = parts[i]
                body = parts[i + 1] if (i + 1) < len(parts) else ""
                full_content = (header + body).strip()

                if full_content:
                    section_chunks.append(Chunk(
                        num_id=global_id,
                        filename=path_obj.path.as_posix(),
                        section_name=rs.section_name,
                        section_num_id=section_internal_id,
                        valid=self._is_content_valid(full_content, rs.exclude_filters, rs.include_filters),
                        content=full_content
                    ))
                    global_id += 1
                    section_internal_id += 1

        return section_chunks

    @staticmethod
    def _is_content_valid(content: str, exclude_patterns: list[str], include_patterns: list[str]) -> bool:
        """
        Refines the list of chunks using a strict 'Exclude First' logic.
        """

        # 1. Check for Exclude Veto (Case-insensitive)
        if any(re.search(p, content, re.M | re.I) for p in exclude_patterns):
            return False
        # 2. Check for Include Permission
        # If no include_filters are defined, everything that wasn't excluded passes.
        if include_patterns:
            if not any(re.search(p, content, re.M | re.I) for p in include_patterns):
                return False

        # got it
        return True


class MaterialTokenizerError(Exception):
    pass
