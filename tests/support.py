"""Shared test helpers for constructing and inspecting current-domain settings."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import fields
from typing import Any

from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExcecutionParameters,
    InputParameters,
    LoggingParameters,
    OutputParameters,
    WorkspaceParameters,
)
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
    ValueOrigin,
    ValueSetting,
    VerboseBoolSetting,
)


def assign(setting: ValueSetting, value: Any, origin: ValueOrigin = ValueOrigin.CLI) -> ValueSetting:
    """Set a ValueSetting using the current immutable-after-first-write API."""
    setting.set(value, origin)
    return setting


def flatten_settings(param_objects: Iterable[Any]) -> list[ValueSetting]:
    """Unwrap parameter dataclasses returned by ConfigurationLoader.run()."""
    found: list[ValueSetting] = []
    for obj in param_objects:
        if isinstance(obj, ValueSetting):
            found.append(obj)
            continue
        try:
            for field in fields(obj):
                value = getattr(obj, field.name)
                if isinstance(value, ValueSetting):
                    found.append(value)
        except TypeError:
            continue
    return found


def setting_of(param_objects: Iterable[Any], cls: type) -> ValueSetting:
    return next(s for s in flatten_settings(param_objects) if isinstance(s, cls))


def blank_parameter_groups() -> dict[str, Any]:
    """Fresh, unset parameter objects matching ConfigurationValidator.run()."""
    aisp = AIServiceParameters(
        APIKeyStringSetting("api_key"),
        TCPKeepAliveBoolSetting("tcp_keep_alive"),
        BaseURLStringSetting("base_url"),
        ModelNameStringSetting("model_name"),
        MaxContextTokensIntSetting("max_context_tokens"),
        MaxOutputTokensIntSetting("max_output_tokens"),
        CharsPerTokenFloatSetting("chars_per_token"),
        TemperatureFloatSetting("temperature"),
        RetryDelayIntSetting("retry_delay"),
        MaxRetryIntSetting("max_retry"),
        CaBundleFilePathSetting("ca_bundle_file"),
        ClientCertFilePathSetting("client_cert_file"),
        ClientKeyFilePathSetting("client_key_file"),
    )
    lp = LoggingParameters(
        DebugBoolSetting("debug"),
        VerboseBoolSetting("verbose"),
        LogFilePathSetting("log_file"),
        ActivityFilePathSetting("activity_file"),
    )
    ep = ExcecutionParameters(
        SimulateBoolSetting("simulate"),
        SequentialProcessingBoolSetting("sequential_processing"),
    )
    ip = InputParameters(
        TaskStringSetting("task"),
        PromptFilePathSetting("prompt_file"),
        LoopFilePathSetting("loop_file"),
        ResourceFilePathSetting("resource_file"),
    )
    op = OutputParameters(
        OutputFilePathSetting("output_file"),
        OutputDirectoryPathSetting("output_directory"),
        OutputDelimiterStringSetting("output_delimiter"),
        OutputModeStringSetting("output_mode"),
        OutputFilenameSchemaStringSetting("output_filename_schema"),
    )
    wp = WorkspaceParameters(
        BaseDirectoryPathSetting("base_directory"),
        ConfigFilePathSetting("config_file"),
    )
    return {"aisp": aisp, "lp": lp, "ep": ep, "ip": ip, "op": op, "wp": wp}
