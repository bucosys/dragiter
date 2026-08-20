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

from json import JSONDecodeError, loads
import logging
from typing import Any

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.settings import LoopFilePathSetting
from dragiter.infrastructure.io.io_services import read_stripped_lines_from_file

logger = logging.getLogger(__name__)


class LoopBuilder(Worker):
    MAX_LOOP_ITEMS: int = 50

    def __init__(self) -> None:
        pass

    def run(self, loop_file_path_setting: LoopFilePathSetting) -> Loop:
        try:
            contents: list[str] = []  # filled with lines from file (if set)
            dict_list: list[dict[str, Any]] = []  # for return purpose

            if loop_file_path_setting.is_set:  # should lines be read?
                contents = read_stripped_lines_from_file(
                    loop_file_path_setting.value
                )  # read lines from file, no empty lines into

                # --- CIRCUIT BREAKER ---
                if len(contents) > self.MAX_LOOP_ITEMS:
                    raise LoopBuilderError(
                        f"Loop file contains {len(contents)} items. "
                        f"Execution aborted. The hard limit is {self.MAX_LOOP_ITEMS}. "
                        f"Please split your loop file into smaller batches and run dragiter multiple times."
                    )

                for index, line in enumerate(contents, start=1):
                    try:
                        data = loads(line)
                        # no error, is it a dict?
                        if isinstance(data, dict):
                            data["LOOP_NUM_ID"] = index
                            dict_list.append(data)
                        else:
                            dict_list.append(
                                {"LOOP_CONTENT": line, "LOOP_NUM_ID": index}
                            )

                    except JSONDecodeError:
                        # not json-l
                        dict_list.append({"LOOP_CONTENT": line, "LOOP_NUM_ID": index})

            # finally return new Loop object (always)
            return Loop(lines=dict_list)

        except Exception as e:
            raise LoopBuilderError(
                f"Failed to load loop data from {loop_file_path_setting.value}: {e}"
            ) from e


class LoopBuilderError(Exception):
    pass
