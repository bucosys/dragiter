# =============================================================================
# dragiter - Deterministic Context Iterator
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
from pathlib import PosixPath

from dragiter.application.core.buffered_activity_logger import BufferedActivityLogger
from dragiter.domain.ports.activity_logger import ActivityLogger
from dragiter.domain.ports.activity_provider import ActivityProvider
from dragiter.domain.ports.checksum_generator import ChecksumGenerator
from dragiter.infrastructure.io.io_services import append_jsonl_to_file


class FileActivityLogger(BufferedActivityLogger):

    def __init__(self) -> None:
        super().__init__()
        self.lines_written: int = 0


    def write_activity(self, activity_provider: ActivityProvider) -> int:
        super().write_activity(activity_provider)
        return self._sync_buffer_to_file()


    def write_exception(self, e: Exception) -> int:
        super().write_exception(e)
        return self._sync_buffer_to_file()



    def _sync_buffer_to_file(self) -> int:

        # find first element w/ key
        activity_file: PosixPath = next((d["activity_file"] for d in self.activity_dict_list if "activity_file" in d), None)
        if activity_file:
            lines_to_write: list[dict] = self.activity_dict_list[self.lines_written:]

            if lines_to_write:
                append_jsonl_to_file(activity_file, lines_to_write)
                self.lines_written = len(self.activity_dict_list)


