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

import logging
from json import JSONDecodeError, loads
from typing import List, Any

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.settings import LoopFilePathSetting
from dragiter.infrastructure.io.io_services import read_stripped_lines_from_file

logger = logging.getLogger(__name__)


class LoopBuilder(Worker):
    def __init__(self) -> None:
        pass

    def run(self, loop_file_path_setting: LoopFilePathSetting) -> Loop:
        # missing: check if file is JSON-L ...
        try:
            contents: List[str] = []  # filled with lines from file (if set)
            dict_list: List[dict[str, Any]] = []  # for return purpose

            if loop_file_path_setting.is_set:  # should lines be read?
                contents = read_stripped_lines_from_file(
                    loop_file_path_setting.value)  # read lines from file, no empty lines into
                for index, line in enumerate(contents, start=1):
                    try:
                        data = loads(line)
                        # no error, is it a dict?
                        if isinstance(data, dict):
                            data["LOOP_NUM_ID"] = index
                            dict_list.append(data)
                        else:
                            dict_list.append({"LOOP_CONTENT": line, "LOOP_NUM_ID": index})

                    except JSONDecodeError as e:
                        # not json-l
                        dict_list.append({"LOOP_CONTENT": line, "LOOP_NUM_ID": index})

            # finally return new Loop object (always)
            return Loop(lines=dict_list)

        except Exception as e:
            raise LoopBuilderError(f"Failed to load loop data.") from e


class LoopBuilderError(Exception):
    pass
