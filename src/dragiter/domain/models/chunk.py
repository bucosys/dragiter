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
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    num_id: int
    filename: str
    section_name: str
    section_num_id: int
    valid: bool
    content: str

    @property
    def formatted_content(self):
        return "=== Chunk {num_id:04d} Filename: {filename} Section: {section_name} ===\n\n{content}".format(
            num_id=self.num_id or 0,
            filename=self.filename,
            section_name=self.section_name,
            content=self.content
        )

    def format_template(self, template: str = "") -> str:
        result = template or ""
        d = {
            "CHUNK_NUM_ID": self.num_id,
            "CHUNK_FILE_NAME": self.filename,
            "CHUNK_SECTION_NAME": self.section_name,
            "CHUNK_SECTION_NUM_ID": self.section_num_id,
            "CHUNK_CONTENT": self.content
        }

        return result.format_map(d)
