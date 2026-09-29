# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

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
    MaxChunksIntSetting,
    MaxRetryIntSetting,
    ModelNameStringSetting,
    OutputDelimiterStringSetting,
    OutputDirectoryPathSetting,
    OutputFilenameSchemaStringSetting,
    OutputFilePathSetting,
    OutputModeStringSetting,
    PackLimitCharsIntSetting,
    PromptFilePathSetting,
    ResourceFilePathSetting,
    ResumeBoolSetting,
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
class ExecutionParameters(ValueSettingsActivityProvider):
    """Runtime behaviour of the context iterator."""
    simulate_bool_setting: SimulateBoolSetting
    sequential_processing_bool_setting: SequentialProcessingBoolSetting
    pack_limit_chars_int_setting: PackLimitCharsIntSetting
    max_chunks_int_setting: MaxChunksIntSetting
    resume_bool_setting: ResumeBoolSetting


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

