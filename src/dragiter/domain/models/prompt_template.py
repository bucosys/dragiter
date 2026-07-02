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
class PromptTemplate:
    instruction: str
    first: str
    material: str
    synthesis: str
    temperature: float
    sequential_processing: bool
    output_filename_schema: str
    output_delimiter: str

    def merge_synthesis_with_loop_dict(self, loop_dict: dict) -> str:
        # validate or bail out
        if loop_dict is not None and len(loop_dict.get("LOOP_CONTENT", "")) > 0:
            # loop_content = loop_element.get("LOOP_CONTENT", "")
            return self.synthesis.format_map(loop_dict)

    def __repr__(self):
        # This is shown in the logger
        return f"PromptTemplate (instruction length ='{len(self.instruction or {})}', task length ='{len(self.first or {})}')"


class PromptTemplateError(Exception):
    pass
