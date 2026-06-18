import logging

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Loop:
    """Immutable container content list"""
    lines: list[dict] = field(default_factory=list)

    def __str__(self) -> str:
        summary = [f"Loop (Total: {len(self.lines)}):"]
        for i, line in enumerate(self.lines):
            summary.append(f"Line {i + 1:03d}: {len(line or "")} chars")
        return " ".join(summary)