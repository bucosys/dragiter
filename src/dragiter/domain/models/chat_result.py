from datetime import datetime
from dataclasses import dataclass, field
from typing import Literal

from dragiter.domain.models.chat_message import ChatMessage

@dataclass
class ChatResult(ChatMessage):
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    finish_reason: str | None = None

