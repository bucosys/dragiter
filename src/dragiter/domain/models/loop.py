import logging

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Loop:
    """Immutable container content list"""
    lines: list[dict] = field(default_factory=list)
