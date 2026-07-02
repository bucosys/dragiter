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
from typing import Literal
from dataclasses import dataclass, field
from typing import Any
from dragiter.domain.models.chunk import Chunk


ChatRoles = Literal["system", "user", "assistant"]


@dataclass
class ChatMessage:
    role: ChatRoles  # who asks / responds ?
    content: str | None = None  # what to ask / respond

    def __str__(self) -> str:
        # Schneidet den Text nach 40 Zeichen ab, damit das Log sauber bleibt
        if self.content:
            snippet = self.content if len(self.content) <= 40 else self.content[:37] + "..."
        else:
            snippet = "None"
        return f"[{self.role.upper()}]: {snippet}"



@dataclass
class ChatSession:
    input_chat_message_list: list[ChatMessage] = field(default_factory=list)

    # The chunk associated with this session.
    # Particularly relevant when sequential_processing is set to True.
    chunk: Chunk | None = None

    # The current loop entry for this session.
    # Can originate from a plain text loop file or a JSONL record
    # (e.g. {"LOOP_CONTENT": "..."} or any JSON object).
    loop_item: dict[str, Any] | None = None

    def __str__(self) -> str:
        msg_count = len(self.input_chat_message_list)
        chunk_info = f", chunk={self.chunk.filename}" if self.chunk else ""
        loop_info = f", loop={self.loop_item}" if self.loop_item else ""
        return f"<ChatSession: {msg_count} inputs{chunk_info}{loop_info}>"


@dataclass
class ChatSessions:
    session_list: list[ChatSession] = field(default_factory=list)

    def __str__(self) -> str:
        summary = [f"ChatSessions (Total: {len(self.session_list)}):"]
        for i, session in enumerate(self.session_list):
            summary.append(f"  {i + 1}. {session}")
        return " ".join(summary)
