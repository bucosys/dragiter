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

from dataclasses import dataclass

from dragiter.domain.models.settings import (
    ActivityFilePathSetting,
    APIKeyStringSetting,
    BaseDirectoryPathSetting,
    BaseURLStringSetting,
    CaBundleFilePathSetting,
    CharsPerTokenFloatSetting,
    ClientCertFilePathSetting,
    ClientKeyFilePathSetting,
    ConfigFilePathSetting,
    DebugBoolSetting,
    LogFilePathSetting,
    LoopFilePathSetting,
    MaxContextTokensIntSetting,
    MaxOutputTokensIntSetting,
    MaxRetryIntSetting,
    ModelNameStringSetting,
    OutputDelimiterStringSetting,
    OutputDirectoryPathSetting,
    OutputFilenameSchemaStringSetting,
    OutputFilePathSetting,
    OutputModeStringSetting,
    PromptFilePathSetting,
    ResourceFilePathSetting,
    RetryDelayIntSetting,
    SequentialProcessingBoolSetting,
    SimulateBoolSetting,
    TaskStringSetting,
    TCPKeepAliveBoolSetting,
    TemperatureFloatSetting,
    VerboseBoolSetting,
)
from dragiter.domain.models.value_settings_activity_provider import ValueSettingsActivityProvider


@dataclass(frozen=True)
class AIServiceParameters(ValueSettingsActivityProvider):
    """Connection, model and transport settings for the LLM client."""
    api_key_string_setting: APIKeyStringSetting
    tcp_keep_alive_bool_setting: TCPKeepAliveBoolSetting
    base_url_string_setting: BaseURLStringSetting
    model_name_string_setting: ModelNameStringSetting
    max_context_token_int_setting: MaxContextTokensIntSetting
    max_output_tokens_int_setting: MaxOutputTokensIntSetting
    chars_per_token_float_setting: CharsPerTokenFloatSetting
    temperature_float_setting: TemperatureFloatSetting
    retry_delay_int_setting: RetryDelayIntSetting
    max_retries_int_setting: MaxRetryIntSetting
    ca_bundle_file_path_setting: CaBundleFilePathSetting
    client_cert_file_path_setting: ClientCertFilePathSetting
    client_key_file_path_setting: ClientKeyFilePathSetting


@dataclass(frozen=True)
class LoggingParameters(ValueSettingsActivityProvider):
    """Verbosity and destination settings for logs and activity traces."""
    debug_bool_setting: DebugBoolSetting
    verbose_bool_setting: VerboseBoolSetting
    log_file_path_setting: LogFilePathSetting
    activity_file_path_setting: ActivityFilePathSetting



@dataclass(frozen=True)
class ExcecutionParameters(ValueSettingsActivityProvider):
    """Runtime behaviour of the context iterator."""
    simulate_bool_setting: SimulateBoolSetting
    sequential_processing_bool_setting: SequentialProcessingBoolSetting


@dataclass(frozen=True)
class InputParameters(ValueSettingsActivityProvider):
    """Sources that define the work item: task text, prompt, loop, resources."""
    task_string_setting: TaskStringSetting
    prompt_file_path_setting: PromptFilePathSetting
    loop_file_path_setting: LoopFilePathSetting
    resource_file_path_setting: ResourceFilePathSetting
    
    
@dataclass(frozen=True)
class OutputParameters(ValueSettingsActivityProvider):
    """Where results are written and how files are named and delimited."""
    output_file_path_setting: OutputFilePathSetting
    output_directory_path_setting: OutputDirectoryPathSetting
    output_delimiter_string_setting: OutputDelimiterStringSetting
    output_mode_string_setting: OutputModeStringSetting
    output_filename_schema_string_setting: OutputFilenameSchemaStringSetting

    
@dataclass(frozen=True)
class WorkspaceParameters(ValueSettingsActivityProvider):
    """Filesystem root and configuration-file location."""
    base_directory_path_setting: BaseDirectoryPathSetting
    config_file_path_setting: ConfigFilePathSetting

