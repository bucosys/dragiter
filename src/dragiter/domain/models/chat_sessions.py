from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

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
class ChatResult:
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    finish_reason: str | None = None

    def __str__(self) -> str:
        # Zeigt nur die wesentlichen Metriken
        return f"Result(tokens_in={self.input_tokens}, tokens_out={self.output_tokens}, duration={self.duration_ms}ms)"


@dataclass
class ChatSession:
    input_chat_message_list: list[ChatMessage] = field(default_factory=list)
    output_chat_message: ChatMessage = field(
        default_factory=lambda: ChatMessage(role="assistant")
    )
    chat_result: ChatResult = field(default_factory=ChatResult)

    def validate(self) -> None:
        """Validates structural constraints for all chat sessions.

        Raises:
            ValueError: If any validation rule is violated.
        """
        #        for index, session in enumerate(self.session_list):
        messages = self.input_chat_message_list

        # Rule 1: At least one "user" message must be present
        has_user = any(msg.role == "user" for msg in messages)
        if not has_user:
            raise ValueError(
                f"Validation error in session {index}: "
                f"The input message list must contain at least one message with the role 'user'."
            )

        # Rule 2: "system" role is only allowed at the very first position (index 0)
        for i, msg in enumerate(messages):
            if msg.role == "system" and i != 0:
                raise ValueError(
                    f"Validation error in session {index}: "
                    f"The 'system' role is only allowed at the first position (index 0). "
                    f"Found at index {i}."
                )

    def __str__(self) -> str:
        # Fasst die Session zusammen
        msg_count = len(self.input_chat_message_list)
        return (f"<ChatSession: {msg_count} inputs | "
                f"Output: {len(self.output_chat_message.content or '')} chars | "
                f"{self.chat_result}>")


@dataclass
class ChatSessions:
    session_list: list[ChatSession] = field(default_factory=list)

    def __str__(self) -> str:
        summary = [f"ChatSessions (Total: {len(self.session_list)}):"]
        for i, session in enumerate(self.session_list):
            summary.append(f"  {i + 1}. {session}")
        return " ".join(summary)
