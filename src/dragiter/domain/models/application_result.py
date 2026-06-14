from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationResult:
    """Exit Code"""
    exit_code: int = 0
