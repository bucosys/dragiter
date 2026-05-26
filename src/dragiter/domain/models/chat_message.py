from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


ChatRoles = Literal["system", "user", "assistent"]
TypeChars = Literal["S", "M", "U", "R"]  # S: System, M: Material, U: User, R: Response (from AI)

@dataclass
class ChatMessage:
    role: ChatRoles # who asks / responds ?
    content: str | None = None   # what to ask / respond


@dataclass
class ChatMessages:
    chat_message_list: list[ChatMessage] = field(default_factory=list)



@dataclass
class ExtendedMessage(ChatMessage):
    type: TypeChars | None = None  # my Type S: System, M: Material, U: User, R: Response
    processed_at: datetime | None = None  # timestamp



@dataclass
class ChatResult(ChatMessage):
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    finish_reason: str | None = None


@dataclass
class ExtendedMessages:
    extended_message_list: list[ExtendedMessage] = field(default_factory=list)
    chat_result: ChatResult = field(default_factory=ChatResult)




