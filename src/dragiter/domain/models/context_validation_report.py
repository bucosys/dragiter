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

from dataclasses import dataclass, field


@dataclass
class ContextValidationReport:
    """Encapsulates the result of context window token estimation and validation."""

    # Did the payload pass validation?
    is_valid: bool

    # Aggregate metrics
    total_tokens: int

    # The configured limit applied during this run
    max_tokens_limit: int

    # The High-Water Mark (Maximal Values)
    max_session_tokens: int = 0
    max_session_index: int = -1

    # Detailed telemetry
    session_token_counts: dict[int, int] = field(default_factory=dict)
    simulation_warnings: list[str] = field(default_factory=list)
