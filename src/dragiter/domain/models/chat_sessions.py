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
class ChatSession:
    input_chat_message_list: list[ChatMessage] = field(default_factory=list)

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
        return (f"<ChatSession: {msg_count} inputs")


@dataclass
class ChatSessions:
    session_list: list[ChatSession] = field(default_factory=list)

    def __str__(self) -> str:
        summary = [f"ChatSessions (Total: {len(self.session_list)}):"]
        for i, session in enumerate(self.session_list):
            summary.append(f"  {i + 1}. {session}")
        return " ".join(summary)
