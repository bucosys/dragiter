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
import datetime
import hashlib
import json
import traceback
from dataclasses import is_dataclass, fields
from typing import Any

from dragiter.domain.ports.activity_logger import ActivityLogger
from dragiter.domain.ports.activity_provider import ActivityProvider



class BufferedActivityLogger(ActivityLogger):

    def __init__(self) -> None:
        self.activity_dict_list: list[dict[str, Any]] = []

    def write_activity(self, activity_provider: ActivityProvider) -> int:

        a_p_dict_list:list[dict[str, Any]] = activity_provider.to_activity_dict_list()

        for d_a in a_p_dict_list:
            enhanced_activity_dict: dict[str, Any] = {
                "TS": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "RT": activity_provider.__class__.__name__
            }
            enhanced_activity_dict.update(d_a)
            self.activity_dict_list.append(enhanced_activity_dict)

        return len(self.activity_dict_list)

    def write_exception(self, e: Exception) -> int:
        dict_e: dict[str, Any] = {
            "type": type(e).__name__,
            "message": str(e),
            "module": type(e).__module__,
            # full stack trace
            "traceback": traceback.format_exc(),
            # optional: first row only for brief understanding
            "location": traceback.extract_tb(e.__traceback__)[-1].line if e.__traceback__ else None,
            "filename": traceback.extract_tb(e.__traceback__)[-1].filename if e.__traceback__ else None,
            "lineno": traceback.extract_tb(e.__traceback__)[-1].lineno if e.__traceback__ else None
        }


        self.activity_dict_list.append(dict_e)
        return 1

