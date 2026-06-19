from dataclasses import dataclass, field
from datetime import datetime

from dragiter.domain.models.chat_sessions import ChatMessage


@dataclass
class ChatResult:
    output_chat_message: ChatMessage = field(
        default_factory=lambda: ChatMessage(role="assistant")
    )
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    finish_reason: str | None = None

    def __str__(self) -> str:
        # Zeigt nur die wesentlichen Metriken
        return f"Result(output_chat_message={len(self.output_chat_message.content or "")} chars, tokens_in={self.input_tokens}, tokens_out={self.output_tokens}, duration={self.duration_ms}ms)"


@dataclass
class ChatResults():
    chat_result_list: list[ChatResult] = field(default_factory=list)

    def __str__(self) -> str:
        summary = [f"ChatResults (Total: {len(self.chat_result_list)}):"]
        for i, result in enumerate(self.chat_result_list):
            summary.append(f"  {i + 1}. {result}")
        return " ".join(summary)
