# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dataclasses import dataclass
import logging

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
        return f"=== Chunk {self.num_id or 0:04d} Filename: {self.filename} Section: {self.section_name} ===\n\n{self.content}"

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
