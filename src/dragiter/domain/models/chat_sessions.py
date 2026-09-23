# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dataclasses import dataclass, field
from typing import Any, Literal

from dragiter.domain.models.chunk import Chunk
from dragiter.domain.common.activity_provider import ActivityProvider

ChatRoles = Literal["system", "user", "assistant"]


@dataclass
class ChatMessage:
    role: ChatRoles  # who asks / responds ?
    content: str | None = None  # what to ask / respond

    def __str__(self) -> str:
        # Truncates the text after 40 characters to keep the log clean
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
class ChatSessions(ActivityProvider):
    session_list: list[ChatSession] = field(default_factory=list)

    def __str__(self) -> str:
        summary = [f"ChatSessions (Total: {len(self.session_list)}):"]
        for i, session in enumerate(self.session_list):
            summary.append(f"  {i + 1}. {session}")
        return " ".join(summary)

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        """
        Returns activity information for logging.
        In verbose mode each individual session is logged in detail.
        """

        # Detailed mode (verbose)
        activity_dicts = []

        if self.session_list:
            # Aggregated summary (default)
            total_sessions = len(self.session_list)
            total_messages = sum(len(s.input_chat_message_list) for s in self.session_list)
            sessions_with_chunks = sum(1 for s in self.session_list if s.chunk is not None)
            sessions_with_loop = sum(1 for s in self.session_list if s.loop_item)

            activity_dicts.append({
                "chat_sessions_count": total_sessions,
                "total_input_messages": total_messages,
                "sessions_with_chunk": sessions_with_chunks,
                "sessions_with_loop_item": sessions_with_loop,
            })

        for i, session in enumerate(self.session_list):
            for msg in session.input_chat_message_list:
                entry = {
                    "session_index": i+1,
                    "role": msg.role,
                    "content": msg.content,
                }
                activity_dicts.append(entry)


        return activity_dicts
