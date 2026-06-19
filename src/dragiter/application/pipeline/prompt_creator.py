from pathlib import Path

from dragiter.application.core.xdi import *
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.settings import PromptFilePathSetting, TaskStringSetting, OutputDelimiterStringSetting, \
    OutputFilenameSchemaStringSetting, TemperatureFloatSetting, SequentialProcessingBoolSetting
from dragiter.infrastructure.io.io_services import read_from_toml, read_stdin_content

logger = logging.getLogger(__name__)


class PromptCreator:
    def __init__(self) -> None:
        pass

    def run(self, task_string_setting: TaskStringSetting,
            prompt_file_path_setting: PromptFilePathSetting,
            sequential_processing_bool_setting: SequentialProcessingBoolSetting,
            output_delimiter_string_setting: OutputDelimiterStringSetting,
            output_filename_schema_string_setting: OutputFilenameSchemaStringSetting,
            temperature_float_setting: TemperatureFloatSetting
            ) -> PromptTemplate:
        # case I nandled prior

        try:
            std_in = read_stdin_content()

            if task_string_setting.is_set:
                return PromptTemplate(instruction=None, first=std_in,
                                      material=None, synthesis=task_string_setting.value,
                                      temperature=(temperature_float_setting.value or 0.0),
                                      sequential_processing=(sequential_processing_bool_setting.value or False),
                                      output_filename_schema=(
                                              output_filename_schema_string_setting.value or "dragiter-out.txt"),
                                      output_delimiter=(output_delimiter_string_setting.value or "\n")
                                      )

            else:
                path: Path = prompt_file_path_setting.value
                logger.debug(f"Try loading prompt content from file: {path.name}")
                toml_result_dict = read_from_toml(path)
                system_sec = toml_result_dict["system"]
                task_sec = toml_result_dict["task"]

                if task_sec.get("first"):
                    task_sec["first"] = self._merge_stdin_into_string(task_sec["first"], std_in)

                # now the specialities
                # a) build defaults
                behaviour_sec = {
                    "behaviour": {
                        "temperature": 0.0,
                        "sequential_processing": False
                    }
                }

                outcome_sec = {
                    "outcome": {
                        "output_delimiter": "\n",
                        "output_filename_schema": "dragiter-out.txt"
                    }
                }

                # b) update with template file values
                behaviour_sec["behaviour"].update(toml_result_dict.get("behaviour", {}))
                outcome_sec["outcome"].update(toml_result_dict.get("outcome", {}))

                # prep return dataclass
                result_prompt_template = PromptTemplate(
                    **system_sec, **task_sec,
                    **behaviour_sec["behaviour"], **outcome_sec["outcome"])

                # if available replace with cli params
                if sequential_processing_bool_setting.is_set:
                    result_prompt_template.sequential_processing = sequential_processing_bool_setting.value

                if output_delimiter_string_setting.is_set:
                    result_prompt_template.output_delimiter = output_delimiter_string_setting.value

                if output_filename_schema_string_setting.is_set:
                    result_prompt_template.output_filename_schema = output_filename_schema_string_setting.value

                if temperature_float_setting.is_set:
                    result_prompt_template.temperature = temperature_float_setting.value

                return result_prompt_template

        except Exception as e:
            # logger.error(f"PromptCreator::run failed: {e}")
            # raise PromptBuilderError(f"Failed to load prompt.") from e
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
