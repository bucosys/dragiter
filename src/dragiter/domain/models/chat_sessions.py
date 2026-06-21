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
