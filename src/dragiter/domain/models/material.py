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
from typing import Any

from dragiter.domain.models.chunk import Chunk
from dragiter.domain.ports.activity_provider import ActivityProvider

logger = logging.getLogger(__name__)


class Material(ActivityProvider):
    def __init__(self, chunks: list[Chunk]):
        """Initialise the configuration object and load settings."""
        # super().__init__()

        self._chunks: list[Chunk] = chunks

        # # local vars
        # material_config_dict: dict[str, dict] = {}
        # mf: Path = Path(config.material_file) if config.material_file else None
        #
        # if mf is not None and mf.exists():
        #     try:
        #         material_config_dict = read_from_toml(mf)
        #         self._chunks = self._process_markdown_configs(material_config_dict)
        #     except Exception as e:
        #         raise MaterialError(f"Failed to load material chunks, defined in file {mf}.") from e
        #
        # if config.debug:
        #     print(f"Loaded {len(self._chunks)} chunks.")

    @property
    def chunks(self):
        return self._chunks

    def __repr__(self):
        # This is shown in the logger
        return f"Material(chunks length ='{len(self._chunks)}'"

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        """
        Returns flat activity records:
        - First record: global summary
        - Then one record per source file (grouped by filename with change detection)
        Preserves the original order of files as they appear in the chunks list.
        """
        if not self._chunks:
            return [{"material_chunks_count": 0}]

        total_chunks = len(self._chunks)
        total_characters = sum(len(chunk.content) for chunk in self._chunks)
        chunk_sizes = [len(chunk.content) for chunk in self._chunks]

        # Global summary (first record)
        global_record: dict[str, Any] = {
            "material_chunks_count": total_chunks,
            "total_characters": total_characters,
            "unique_sources": len({c.filename for c in self._chunks}),
            "average_chunk_size": round(total_characters / total_chunks, 1) if total_chunks > 0 else 0,
            "max_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
            "min_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
        }

        activity_records = [global_record]

        # Group by file with change detection (preserves order)
        current_file = None
        current_sizes: list[int] = []
        file_num = 1

        for chunk in self._chunks:
            filename = chunk.filename

            if filename != current_file and current_file is not None:
                # File changed → output stats for previous file
                self._append_file_record(activity_records, file_num, current_file, current_sizes)
                file_num += 1
                current_sizes = []

            current_file = filename
            current_sizes.append(len(chunk.content))

        # Last group
        if current_file is not None:
            self._append_file_record(activity_records, file_num, current_file, current_sizes)

        return activity_records

    def _append_file_record(self, records: list, file_num: int, filename: str, sizes: list[int]):
        """Append one flat record per file."""
        num_chunks = len(sizes)
        records.append({
            "file_num": file_num,
            "file": filename,
            "num_chunks": num_chunks,
            "min_chunk_size": min(sizes),
            "max_chunk_size": max(sizes),
            "avg_chunk_size": round(sum(sizes) / num_chunks, 1) if num_chunks > 0 else 0,
        })