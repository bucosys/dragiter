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

from dragiter.domain.models.chunk import Chunk

logger = logging.getLogger(__name__)


class Material():
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
