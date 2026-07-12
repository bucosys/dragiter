# =============================================================================
# dragiter - Deterministic RAG Iterator
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

import os
from dataclasses import dataclass
from pathlib import Path

# from dragiter.application.config.configuration_decorators import *
from dragiter.application.core.xdi import *
from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.input_path_parameters import InputPathParameters
from dragiter.domain.models.output_parameters import OutputParameters
from dragiter.domain.models.processing_parameters import ProcessingParameters
from dragiter.domain.models.settings import (
    SimulateBoolSetting, VerboseBoolSetting,
    ApiKeyStringSetting, BaseURLStringSetting, ModelNameStringSetting,
    OutputModeStringSetting, TaskStringSetting, MaxContextTokensIntSetting, MaxOutputTokensIntSetting,
    CharsPerTokenFloatSetting, BaseDirectoryPathSetting, ActivityFilePathSetting, ConfigFilePathSetting,
    PromptFilePathSetting, LoopFilePathSetting, OutputFilePathSetting, OutputDirectoryPathSetting,
    ResourceFilePathSetting, ValueSetting, PathSetting, TemperatureFloatSetting, MaxRetryIntSetting,
    RetryDelayIntSetting, DebugBoolSetting, SequentialProcessingBoolSetting, LogFilePathSetting)

logger = logging.getLogger(__name__)


# Configuration Validator Issue (CVI)
@dataclass
class ConfigurationValidatorFinding:
    rule: str
    finding: str
    description: str = None


class ConfigurationValidator:
    def __init__(self) -> None:
        """Modify and validate the configuration"""

    def run(self,
            api_key_string_setting: ApiKeyStringSetting,
            base_url_string_setting: BaseURLStringSetting,
            model_name_string_setting: ModelNameStringSetting,
            output_mode_string_setting: OutputModeStringSetting,
            task_string_setting: TaskStringSetting,
            chars_per_token_float_setting: CharsPerTokenFloatSetting,
            max_output_token_int_setting: MaxOutputTokensIntSetting,
            max_context_token_int_setting: MaxContextTokensIntSetting,
            temperature_float_setting: TemperatureFloatSetting,
            retry_delay_int_setting: RetryDelayIntSetting,
            max_retries_int_setting: MaxRetryIntSetting,
            activity_file_path_setting: ActivityFilePathSetting,
            base_directory_path_setting: BaseDirectoryPathSetting,
            config_file_path_setting: ConfigFilePathSetting,
            logfile_path_setting: LogFilePathSetting,
            prompt_file_path_setting: PromptFilePathSetting,
            loop_file_path_setting: LoopFilePathSetting,
            resource_file_path_setting: ResourceFilePathSetting,
            output_file_path_setting: OutputFilePathSetting,
            output_directory_path_setting: OutputDirectoryPathSetting,
            debug_bool_setting: DebugBoolSetting,
            simulate_bool_setting: SimulateBoolSetting,
            verbose_bool_setting: VerboseBoolSetting,
            sequencial_processing_bool_setting: SequentialProcessingBoolSetting,
            ) -> list[ValueSetting]:

        try:

            CVF = ConfigurationValidatorFinding  # shorthand
            cvfs: list[CVF] = []

            # check I: must-have-settings
            if not base_directory_path_setting.is_set:
                base_directory_path_setting.value = Path.cwd()

            # rebase all if nessessary
            if base_directory_path_setting.value != Path.cwd():
                # stage 1 check for reading a file or director
                settings_to_rebase: list[PathSetting] = [
                    activity_file_path_setting,
                    prompt_file_path_setting,
                    loop_file_path_setting,
                    resource_file_path_setting,
                    output_file_path_setting,
                    output_directory_path_setting]

                logger.debug(f"<Rebase path settings to: {base_directory_path_setting.value}>")
                for setting in settings_to_rebase:
                    if setting.is_set:
                        setting.rebase(base_directory_path_setting.value)
                        logger.debug(f"[{setting.key}: {setting.value}]")

            if task_string_setting.is_set:  # so if user choose that param
                if task_string_setting.value.strip() == '':
                    cvfs.append(CVF(task_string_setting.key, "value not set", "No task recognizable"))
            else:  # there will no prompt file read in...
                if not prompt_file_path_setting.is_set:
                    cvfs.append(CVF(prompt_file_path_setting.key, "value not set", "Path to prompt file is mandatory."))
                else:
                    pfps_value = prompt_file_path_setting.value
                    if not os.access(pfps_value, os.R_OK):
                        cvfs.append(CVF(prompt_file_path_setting.key,
                                        f"File not readable: {pfps_value}",
                                        "Path to prompt file is mandatory. The given file is not readable."))

            if not simulate_bool_setting.value and not base_url_string_setting.is_set:
                cvfs.append(CVF(base_url_string_setting.key, "value not set", "Path to LLM is mandatory."))

            # check II get file access modifier
            # set default to 'x'
            if not output_mode_string_setting.is_set: output_mode_string_setting.value = "x"
            if not output_mode_string_setting.value in {'a', 'x', 'w'}:
                cvfs.append(CVF(output_mode_string_setting.key,
                                f"If file open mode is set, use one of a (append), w (overwrite) or x (exclusive)"))

            # stage 1 check for reading a file or director
            input_path_settings_to_check = [base_directory_path_setting, loop_file_path_setting,
                                            resource_file_path_setting, output_directory_path_setting]

            cvfs.extend([
                CVF(setting.key, f"Path not readable: {setting.value}")
                for setting in input_path_settings_to_check
                if setting.is_set and not os.access(setting.value, os.R_OK)
            ])

            # stage II check for wrinting a sinle file, check directory
            output_path_settings_to_check = [activity_file_path_setting, logfile_path_setting, output_file_path_setting]

            cvfs.extend([
                CVF(setting.key, f"Directory not readable: {setting.value.parent}")
                for setting in output_path_settings_to_check
                if setting.is_set and not os.access(setting.value.parent, os.R_OK)
            ])

            # stage III: LLM settings
            if max_retries_int_setting.is_set:
                if max_retries_int_setting.value < 0 or max_retries_int_setting.value > 9:
                    cvfs.append(CVF(max_retries_int_setting.key,
                                    f"value should be between 0 and 9 inclusive, not {max_retries_int_setting.value}"))

            if retry_delay_int_setting.is_set:
                if retry_delay_int_setting.value < 0 or retry_delay_int_setting.value > 20:
                    cvfs.append(CVF(retry_delay_int_setting.key,
                                    f"value should be between 0 and 20 inclusive, not {retry_delay_int_setting.value}"))

            if chars_per_token_float_setting.is_set:
                if chars_per_token_float_setting.value <= 0.0:
                    cvfs.append(CVF(chars_per_token_float_setting.key,
                                    f"value should not be less than 0.0: {chars_per_token_float_setting.value}"))

            # stage V: Create AIServiceParameters:
            ai_service_parameters: AIServiceParameters = AIServiceParameters(
                api_key_string_setting, base_url_string_setting, model_name_string_setting,
                max_context_token_int_setting,
                max_output_token_int_setting, chars_per_token_float_setting, temperature_float_setting,
                retry_delay_int_setting,
                max_retries_int_setting
            )

            # stage VI: Create ProcessingParameters
            processing_parameters: ProcessingParameters = ProcessingParameters(
                debug_bool_setting, verbose_bool_setting, simulate_bool_setting, sequencial_processing_bool_setting
            )

            # stage VII: InputFile Parameters
            input_file_parameters: InputPathParameters = InputPathParameters(
                base_directory_path_setting, config_file_path_setting, prompt_file_path_setting,
                loop_file_path_setting, resource_file_path_setting
            )

            # stage VII: Output Parameters (files and options
            output_parameters: OutputParameters = OutputParameters(
                output_directory_path_setting, output_file_path_setting, output_mode_string_setting,
                activity_file_path_setting, logfile_path_setting, output_directory_path_setting,
                output_file_path_setting
            )

            if len(cvfs) > 0: raise ConfigurationValidatorError(cvfs)

            all_checked_elements = [
                base_url_string_setting,
                model_name_string_setting,
                output_mode_string_setting,
                task_string_setting,
                max_retries_int_setting,
                retry_delay_int_setting,
                activity_file_path_setting,
                base_directory_path_setting,
                config_file_path_setting,
                prompt_file_path_setting,
                loop_file_path_setting,
                resource_file_path_setting,
                output_file_path_setting,
                output_directory_path_setting,
                simulate_bool_setting]

            if verbose_bool_setting.value:
                for element in all_checked_elements:
                    logger.debug(f"QC PASSED: [{element.key}: {element.value}]")

            # trick append ai_service_parameter at this time, useful for activity logging as well:
            all_checked_elements.append(processing_parameters)
            all_checked_elements.append(input_file_parameters)
            all_checked_elements.append(output_parameters)
            all_checked_elements.append(ai_service_parameters)

            return all_checked_elements

        except ConfigurationValidatorError as exc:
            raise  #
        except Exception as e:
            raise ConfigurationValidatorError(f"Unexpected exception occured: {e}") from e


class ConfigurationValidatorError(Exception):
    pass
