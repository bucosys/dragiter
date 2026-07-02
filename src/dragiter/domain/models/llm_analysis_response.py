# =============================================================================
# dragiter - Deterministic RAG Iterator
# Copyright (c) 2026 Michael Buchold <michael.buchold@dragiter.app>
#
# This file is part of dragiter.
#
# dragiter is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dragiter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with dragiter. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing (closed-source use, SaaS, etc.), please contact:
# Michael Buchold <michael.buchold@dragiter.app>
# =============================================================================

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
