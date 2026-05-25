from pathlib import Path

from dragiter.domain.models.settings import PromptFilePathSetting, TaskStringSetting
from dragiter.application.core.xdi import *
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.infrastructure.io.io_services import read_from_toml, read_stdin_content

logger = logging.getLogger(__name__)

class PromptCreator:
    def __init__(self) -> None:
        pass



    def run(self, task_string_setting: TaskStringSetting, prompt_file_path_setting: PromptFilePathSetting) -> PromptTemplate:
        # case I nandled prior

        try:
            std_in = read_stdin_content()

            if task_string_setting.is_set:
                return PromptTemplate(instruction=None, first=std_in, material=None, synthesis=task_string_setting.value)

            else:
                path: Path = prompt_file_path_setting.value
                logger.debug(f"Try loading prompt content from file: {path.name}")
                toml_result_dict = read_from_toml(path)
                system_sec = toml_result_dict["system"]
                task_sec = toml_result_dict["task"]

                if task_sec.get("first"):
                    task_sec["first"] = self._merge_stdin_into_string(task_sec["first"], std_in)

                output_sec = toml_result_dict["output"]

                return PromptTemplate(**system_sec, **task_sec, **output_sec)

        except Exception as e:
            #logger.error(f"PromptCreator::run failed: {e}")
            #raise PromptBuilderError(f"Failed to load prompt.") from e
            raise PromptBuilderError(f"PromptCreator::run failed: {e}") from e


    def _merge_stdin_into_string(self, target_string: str, stdin_content: str) -> str:
        """
        Replaces {STDIN} placeholder with content if present.
        If placeholder is missing, returns the original string.
        """
        # if stdin not available we use a zero string
        content_to_insert = stdin_content if stdin_content else ""

        # Wir prüfen explizit auf den Platzhalter, um unnötige Operationen zu sparen
        if "{STDIN}" in target_string:
            return target_string.replace("{STDIN}", content_to_insert)

        return target_string


class PromptBuilderError(Exception):
    pass