# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import datetime
import traceback
from typing import Any

from dragiter import __tool_name__, __version__
from dragiter.domain.ports.activity_logger import ActivityLogger
from dragiter.domain.ports.activity_provider import ActivityProvider


class BufferedActivityLogger(ActivityLogger):

    def __init__(self) -> None:
        self.activity_dict_list: list[dict[str, Any]] = [
            {
                "TS": datetime.datetime.now(datetime.UTC),
                "RT": self.__class__.__bases__[0].__name__, # first superclass
                "initial_status_message": f"{__tool_name__}({__version__}) process started",
            }
        ]

    def write_activity(self, activity_provider: ActivityProvider) -> int:
        date_time_now: datetime.datetime = datetime.datetime.now(datetime.UTC)
        a_p_dict_list:list[dict[str, Any]] = activity_provider.to_activity_dict_list()

        for d_a in a_p_dict_list:
            enhanced_activity_dict: dict[str, Any] = {
                "TS": date_time_now,
                "RT": activity_provider.__class__.__name__
            }
            enhanced_activity_dict.update(d_a)
            self.activity_dict_list.append(enhanced_activity_dict)

        return len(self.activity_dict_list)

    def write_exception(self, e: Exception) -> int:
        dict_e: dict[str, Any] = {
            "TS": datetime.datetime.now().isoformat(),
            "RT": "Exception",
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

