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
        Always returns the same consistent fields for activity logging,
        independent of data volume. Uses aggregation to stay efficient.
        """
        total_chunks = len(self._chunks)

        # Aggregate statistics
        total_characters = sum(len(chunk.content) for chunk in self._chunks)

        # Count unique source files. We use a set comprehension for deduplication.
        # Only chunks that actually have a 'filename' attribute are considered.
        unique_sources = len({chunk.filename for chunk in self._chunks if hasattr(chunk, 'filename')})

        # Alternative (more robust) version - kept as backup:
        # sources = set()
        # for chunk in self._chunks:
        #     filename = getattr(chunk, 'filename', None)
        #     if filename:
        #         sources.add(str(filename))  # str() hardening
        # unique_sources = len(sources)

        # Basic chunk size statistics
        chunk_sizes = [len(chunk.content) for chunk in self._chunks]
        avg_chunk_size = round(total_characters / total_chunks, 1) if total_chunks > 0 else 0
        max_chunk_size = max(chunk_sizes) if chunk_sizes else 0
        min_chunk_size = min(chunk_sizes) if chunk_sizes else 0

        activity_dict: dict[str, Any] = {
            "material_chunks_count": total_chunks,
            "total_characters": total_characters,
            "unique_sources": unique_sources,
            "average_chunk_size": avg_chunk_size,
            "max_chunk_size": max_chunk_size,
            "min_chunk_size": min_chunk_size,
            "has_chunks": total_chunks > 0
        }


        logger.debug(f"Material activity: {total_chunks} chunks, "
                     f"{total_characters:,} characters, {unique_sources} unique sources")

        return [activity_dict]