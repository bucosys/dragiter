# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dataclasses import dataclass
from typing import Any

from dragiter import __tool_name__, __version__
from dragiter.domain.common.activity_provider import ActivityProvider


@dataclass(frozen=True)
class ApplicationResult(ActivityProvider):
    """Exit Code"""
    exit_code: int = 0

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        """
        Final activity entry that clearly signals the completion of the entire process.
        """
        status_text = "SUCCESS" if self.exit_code == 0 else "FAILURE"
        final_summary = {"final_status_message": f"{__tool_name__}({__version__}) process finished with {status_text}"}
        return [final_summary]
