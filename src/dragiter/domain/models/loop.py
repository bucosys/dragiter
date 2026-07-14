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

from dragiter.domain.ports.activity_provider import ActivityProvider

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Loop(ActivityProvider):
    """Immutable container content list"""
    lines: list[dict] = field(default_factory=list)

    def __str__(self) -> str:
        summary = [f"Loop (Total: {len(self.lines)}):"]
        for i, line in enumerate(self.lines):
            summary.append(f"Line {i + 1:03d}: {len(line or "")} chars")
        return " ".join(summary)

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        """
        Consistent activity logging for loop data.
        Always returns the same set of fields regardless of data volume.
        """
        total_items = len(self.lines)

        # === Calculations with explanations ===
        total_keys = sum(
            len(item.keys())
            for item in self.lines
            if isinstance(item, dict)
        )  # Sum of all keys across every dictionary item

        has_json_structure = any(
            isinstance(item, dict) and len(item) > 1
            for item in self.lines
        )  # True if at least one item has multiple key-value pairs (structured JSONL)

        activity_dict: dict[str, Any] = {
            "loop_items_count": total_items,                    # Total number of loop iterations / items
            "has_json_structure": has_json_structure,           # Indicates rich structured data vs. simple lines
            "average_keys_per_item": round(total_keys / total_items, 1)
                                     if total_items > 0 else 0,   # Average fields per item
            "total_keys_across_all_items": total_keys,          # Overall key count - indicator of data richness
        }

        logger.debug(f"Loop activity: {total_items} items "
                     f"({'JSON structure' if has_json_structure else 'simple lines'})")

        return [activity_dict]