# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dataclasses import dataclass, field
from typing import Any

from dragiter.domain.common.activity_provider import ActivityProvider


@dataclass
class ContextValidationReport(ActivityProvider):
    """Encapsulates the result of context window token estimation and validation."""

    # Did the payload pass validation?
    # None when estimation is not applicable (token settings unset).
    is_valid: bool | None

    # Aggregate metrics
    total_tokens: int

    # The configured limit applied during this run.
    # None when estimation is not applicable.
    max_tokens_limit: int | None

    # The High-Water Mark (Maximal Values)
    max_session_tokens: int | None = None
    max_session_index: int = -1

    # Detailed telemetry
    session_token_counts: dict[int, int] = field(default_factory=dict)
    session_input_token_counts: dict[int, int] = field(default_factory=dict)
    simulation_warnings: list[str] = field(default_factory=list)

    chars_per_token: float | None = None
    max_output_tokens: int | None = None

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        activity_dicts: list[dict[str, Any]] = [
            {
                "is_valid": self.is_valid,
                "chars_per_token": self.chars_per_token,
                "max_context_tokens": self.max_tokens_limit,
                "max_output_tokens": self.max_output_tokens,
                "total_tokens": self.total_tokens,
                "max_session_tokens": self.max_session_tokens,
                "max_session_index": self.max_session_index,
                "simulation_warnings": self.simulation_warnings,
            }
        ]
        for index, tot_tokens in self.session_token_counts.items():
            activity_dicts.append(
                {
                    "session_index": index + 1,
                    "estimated_input_tokens": self.session_input_token_counts.get(index),
                    "reserved_output_tokens": self.max_output_tokens,
                    "calculated_total_tokens": tot_tokens,
                    "max_context_tokens": self.max_tokens_limit,
                }
            )
        return activity_dicts
