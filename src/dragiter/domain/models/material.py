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
        - First record: global summary (now includes valid/invalid selection)
        - Then one record per source file (grouped by filename with change detection)
        Preserves the original order of files as they appear in the chunks list.
        """
        if not self._chunks:
            return [{"material_chunks_count": 0}]

        total_chunks = len(self._chunks)
        valid_chunks = [c for c in self._chunks if c.valid]
        invalid_chunks = [c for c in self._chunks if not c.valid]
        
        total_characters = sum(len(chunk.content) for chunk in self._chunks)
        valid_characters = sum(len(chunk.content) for chunk in valid_chunks)

        chunk_sizes = [len(chunk.content) for chunk in self._chunks]

        # Global summary (first record)
        global_record: dict[str, Any] = {
            "material_chunks_count": total_chunks,
            "material_valid_chunks_count": len(valid_chunks),
            "material_invalid_chunks_count": len(invalid_chunks),
            "material_valid_share": round(len(valid_chunks) / total_chunks, 3) if total_chunks else 0.0,
            "total_characters": total_characters,
            "valid_characters": valid_characters,
            "unique_sources": len({c.filename for c in self._chunks}),
            "average_chunk_size": round(total_characters / total_chunks, 1) if total_chunks > 0 else 0,
            "max_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
            "min_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
        }

        activity_records = [global_record]

        # Group by file with change detection (preserves order)
        current_file = None
        current_sizes: list[int] = []
        current_valid: list[bool] = []
        file_num = 1

        for chunk in self._chunks:
            filename = chunk.filename

            if filename != current_file and current_file is not None:
                # File changed → output stats for previous file
                self._append_file_record(activity_records, file_num, current_file, current_sizes, current_valid)
                file_num += 1
                current_sizes = []
                current_valid = []

            current_file = filename
            current_sizes.append(len(chunk.content))
            current_valid.append(chunk.valid)

        # Last group
        if current_file is not None:
            self._append_file_record(activity_records, file_num, current_file, current_sizes, current_valid)

        return activity_records

    def _append_file_record(self, records: list, file_num: int, filename: str, sizes: list[int], valid_flags: list[bool],):
        """Append one flat record per file."""
        num_chunks = len(sizes)
        num_valid = sum(1 for v in valid_flags if v)
        records.append({
            "file_num": file_num,
            "file": filename,
            "num_chunks": num_chunks,
            "num_valid_chunks": num_valid,
            "num_invalid_chunks": num_chunks - num_valid,
            "min_chunk_size": min(sizes) if sizes else 0,
            "max_chunk_size": max(sizes) if sizes else 0,
            "avg_chunk_size": round(sum(sizes) / num_chunks, 1) if num_chunks else 0,
        })
