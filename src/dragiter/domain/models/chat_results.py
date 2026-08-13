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
from datetime import datetime
from typing import Any

from dragiter.domain.models.chat_sessions import ChatMessage
from dragiter.domain.ports.activity_provider import ActivityProvider


@dataclass
class ChatResult:
    output_chat_message: ChatMessage = field(
        default_factory=lambda: ChatMessage(role="assistant")
    )
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    finish_reason: str | None = None

    def __str__(self) -> str:
        # Shows useful metrics
        return f"Result(output_chat_message={len(self.output_chat_message.content or "")} chars, tokens_in={self.input_tokens}, tokens_out={self.output_tokens}, duration={self.duration_ms}ms)"


@dataclass
class ChatResults(ActivityProvider):
    chat_result_list: list[ChatResult] = field(default_factory=list)

    def __str__(self) -> str:
        summary = [f"ChatResults (Total: {len(self.chat_result_list)}):"]
        for i, result in enumerate(self.chat_result_list):
            summary.append(f"  {i + 1}. {result}")
        return " ".join(summary)

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        """
        Returns activity information for logging.
        In verbose mode each individual result is logged in detail.
        """
        activity_dicts = []

        if self.chat_result_list:
            # Aggregated summary
            total_results = len(self.chat_result_list)
            total_input_tokens = sum(r.input_tokens or 0 for r in self.chat_result_list)
            total_output_tokens = sum(r.output_tokens or 0 for r in self.chat_result_list)
            total_duration = sum(r.duration_ms or 0 for r in self.chat_result_list)

            activity_dicts.append({
                "chat_results_count": total_results,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_duration_ms": total_duration,
                "has_results": total_results > 0
            })

        # Detailed mode (verbose)
        for i, result in enumerate(self.chat_result_list):
            entry = {
                "result_index": i + 1,
                "output_chars": len(result.output_chat_message.content or ""),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "duration_ms": result.duration_ms,
                "finish_reason": result.finish_reason,
                "role": result.output_chat_message.role or "",
                "content": result.output_chat_message.content or "",
            }
            activity_dicts.append(entry)

        return activity_dicts