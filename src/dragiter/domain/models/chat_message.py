from dataclasses import dataclass, field
from typing import Literal

ChatRoles = Literal["system", "user", "assistent"]

@dataclass
class ChatMessage:
    role: ChatRoles # who asks / responds ?
    content: str | None = None   # what to ask / respond


@dataclass
class ChatMessages:
    chat_message_list: list[ChatMessage] = field(default_factory=list)



