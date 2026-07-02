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

from dataclasses import dataclass, field
from datetime import datetime

from dragiter.domain.models.chat_sessions import ChatMessage


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
class ChatResults():
    chat_result_list: list[ChatResult] = field(default_factory=list)

    def __str__(self) -> str:
        summary = [f"ChatResults (Total: {len(self.chat_result_list)}):"]
        for i, result in enumerate(self.chat_result_list):
            summary.append(f"  {i + 1}. {result}")
        return " ".join(summary)
