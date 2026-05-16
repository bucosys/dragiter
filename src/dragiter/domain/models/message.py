from dataclasses import dataclass
from typing import Literal

Roles = Literal["system", "user", "assistent"]

@dataclass
class Message:
    role: Roles # who asks / responds ?
    content: str | None = None    # what to ask / respond


