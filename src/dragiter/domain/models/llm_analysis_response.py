import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class AIAnalysisResponse:
    # 1. Identification & Traceability
    file_name: str
    chapter_id: str  # e.g., "005"
    timestamp: float = field(default_factory=time.time)

    # 2. The Core Content (The actual AI result)
    summary: str = ""
    entities: List[str] = field(default_factory=list)
    key_findings: List[str] = field(default_factory=list)

    # 3. Technical Metadata (For debugging/logging)
    model_used: str = "gpt-4-turbo"
    raw_json: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True
    error_message: Optional[str] = None