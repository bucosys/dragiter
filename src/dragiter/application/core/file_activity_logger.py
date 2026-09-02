# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from pathlib import PosixPath

from dragiter.application.core.buffered_activity_logger import BufferedActivityLogger
from dragiter.domain.ports.activity_provider import ActivityProvider
from dragiter.infrastructure.io.io_services import append_jsonl_to_file


class FileActivityLogger(BufferedActivityLogger):

    def __init__(self) -> None:
        super().__init__()

        self.activity_file_found: bool = False
        self.activity_file_path: PosixPath | None = None


    def write_activity(self, activity_provider: ActivityProvider) -> int:
        super().write_activity(activity_provider)
        return self._sync_buffer_to_file()


    def write_exception(self, e: Exception) -> int:
        super().write_exception(e)
        return self._sync_buffer_to_file()



    def _sync_buffer_to_file(self) -> int:

        # find first element w/ key
        if not self.activity_file_found:
            for d in self.activity_dict_list:
                if "activity_file" in d:
                    self.activity_file_found = True
                    self.activity_file_path = d["activity_file"]
                    break

        if self.activity_file_found and self.activity_file_path is None:
            self.activity_dict_list.clear()
            return 0



        if self.activity_file_path and self.activity_dict_list:
            append_jsonl_to_file(self.activity_file_path, self.activity_dict_list)
            lines_written = len(self.activity_dict_list)
            self.activity_dict_list.clear()
            return lines_written

        ##fallback
        return 0
