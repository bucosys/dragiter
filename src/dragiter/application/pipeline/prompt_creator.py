# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import logging
from pathlib import Path

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExecutionParameters,
    InputParameters,
    OutputParameters,
)
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.infrastructure.io.io_services import read_from_toml, read_stdin_content

logger = logging.getLogger(__name__)


class PromptCreator(Worker):
    def __init__(self) -> None:
        pass

    def run(self,
            ip: InputParameters,
            ep: ExecutionParameters,
            op: OutputParameters,
            aisp: AIServiceParameters,
            ) -> PromptTemplate:


        try:
            std_in = read_stdin_content()

            if ip.task_string_setting.is_set:
                return PromptTemplate(instruction=None, first=std_in,
                                      material=None, synthesis=ip.task_string_setting.value,
                                      temperature=(aisp.temperature_float_setting.value or 0.0),
                                      sequential_processing=(ep.sequential_processing_bool_setting.value or False),
                                      output_filename_schema=(
                                              op.output_filename_schema_string_setting.value or "dragiter-out.txt"),
                                      output_delimiter=(op.output_delimiter_string_setting.value or "\n")
                                      )

            else:
                path: Path = ip.prompt_file_path_setting.value
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
                if ep.sequential_processing_bool_setting.is_set:
                    result_prompt_template.sequential_processing = ep.sequential_processing_bool_setting.value

                if op.output_delimiter_string_setting.is_set:
                    result_prompt_template.output_delimiter = op.output_delimiter_string_setting.value

                if op.output_filename_schema_string_setting.is_set:
                    result_prompt_template.output_filename_schema = op.output_filename_schema_string_setting.value

                if aisp.temperature_float_setting.is_set:
                    result_prompt_template.temperature = aisp.temperature_float_setting.value

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

        if "{STDIN}" in target_string:
            return target_string.replace("{STDIN}", content_to_insert)

        return target_string


class PromptBuilderError(Exception):
    pass
