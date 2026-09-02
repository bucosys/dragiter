# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

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
