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

from dataclasses import dataclass
from typing import Any

from dragiter import __tool_name__, __version__
from dragiter.domain.ports.activity_provider import ActivityProvider


@dataclass(frozen=True)
class ApplicationResult(ActivityProvider):
    """Exit Code"""
    exit_code: int = 0

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        """
        Final activity entry that clearly signals the completion of the entire process.
        """
        status_text = "SUCCESS" if self.exit_code == 0 else "FAILURE"
        final_summary = {"final_status_message": f"{__tool_name__}({__version__}) process finished with {status_text}"}
        return [final_summary]
