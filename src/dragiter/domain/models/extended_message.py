from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from dragiter.domain.models.chat_message import ChatMessage

TypeChars = Literal["S", "M", "U", "R"] # S: System, M: Material, U: User, R: Response (from AI)
Roles = Literal["system", "user", "assistent"]

@dataclass
class ExtendedMessage(ChatMessage):
    type: TypeChars | None = None     # my Type S: System, M: Material, U: User, R: Response
    processed_at: datetime | None = None # timestamp
    reuse: bool = False    # for next query



