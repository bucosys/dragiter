from json import JSONDecodeError, loads

from dragiter.application.core.xdi import *
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.settings import LoopFilePathSetting
from dragiter.infrastructure.io.io_services import read_stripped_lines_from_file

logger = logging.getLogger(__name__)


class LoopBuilder:
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
                for line in contents:
                    try:
                        data = loads(line)
                        # no error, is it a dict?
                        if isinstance(data, dict):
                            dict_list.append(data)
                        else:
                            dict_list.append({"LOOP_CONTENT": line})

                    except JSONDecodeError as e:
                        # not json-l
                        dict_list.append({"LOOP_CONTENT": line})

            # finally return new Loop object (always)
            return Loop(lines=dict_list)

        except Exception as e:
            raise LoopBuilderError(f"Failed to load loop data.") from e


class LoopBuilderError(Exception):
    pass
