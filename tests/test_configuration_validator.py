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

"""
Unit tests for ConfigurationValidator.

These tests exercise the mandatory-field rules, range checks and the
simulate-mode exception for base_url — the rules that decide whether a
run is allowed to start at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dragiter.application.config.configuration_validator import (
    ConfigurationValidator,
    ConfigurationValidatorError,
)
from dragiter.domain.models.settings import (
    ActivityFilePathSetting,
    ApiKeyStringSetting,
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
    TemperatureFloatSetting,
    VerboseBoolSetting,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _blank_settings() -> dict:
    """Fresh, unset settings matching the ConfigurationValidator.run() signature."""
    return {
        "api_key_string_setting": ApiKeyStringSetting(_key="api_key"),
        "base_url_string_setting": BaseURLStringSetting(_key="base_url"),
        "model_name_string_setting": ModelNameStringSetting(_key="model_name"),
        "output_mode_string_setting": OutputModeStringSetting(_key="output_mode"),
        "task_string_setting": TaskStringSetting(_key="task"),
        "chars_per_token_float_setting": CharsPerTokenFloatSetting(
            _key="chars_per_token"
        ),
        "max_output_token_int_setting": MaxOutputTokensIntSetting(
            _key="max_output_tokens"
        ),
        "max_context_token_int_setting": MaxContextTokensIntSetting(
            _key="max_context_tokens"
        ),
        "temperature_float_setting": TemperatureFloatSetting(_key="temperature"),
        "retry_delay_int_setting": RetryDelayIntSetting(_key="retry_delay"),
        "max_retries_int_setting": MaxRetryIntSetting(_key="max_retry"),
        "activity_file_path_setting": ActivityFilePathSetting(_key="activity_file"),
        "base_directory_path_setting": BaseDirectoryPathSetting(_key="base_directory"),
        "config_file_path_setting": ConfigFilePathSetting(_key="config_file"),
        "ca_bundle_file_path_setting": CaBundleFilePathSetting(_key="ca_bundle_file"),
        "client_cert_file_path_setting": ClientCertFilePathSetting(
            _key="client_cert_file"
        ),
        "client_key_file_path_setting": ClientKeyFilePathSetting(
            _key="client_key_file"
        ),
        "logfile_path_setting": LogFilePathSetting(_key="log_file"),
        "prompt_file_path_setting": PromptFilePathSetting(_key="prompt_file"),
        "loop_file_path_setting": LoopFilePathSetting(_key="loop_file"),
        "resource_file_path_setting": ResourceFilePathSetting(_key="resource_file"),
        "output_file_path_setting": OutputFilePathSetting(_key="output_file"),
        "output_directory_path_setting": OutputDirectoryPathSetting(
            _key="output_directory"
        ),
        "debug_bool_setting": DebugBoolSetting(_key="debug"),
        "simulate_bool_setting": SimulateBoolSetting(_key="simulate"),
        "verbose_bool_setting": VerboseBoolSetting(_key="verbose"),
        "sequential_processing_bool_setting": SequentialProcessingBoolSetting(
            _key="sequential_processing"
        ),
        "output_delimiter_string_setting": OutputDelimiterStringSetting(
            _key="output_delimiter"
        ),
        "output_filename_schema_string_setting": OutputFilenameSchemaStringSetting(
            _key="output_filename_schema"
        ),
    }


def _findings(exc: ConfigurationValidatorError) -> str:
    """Flatten the error payload into a single searchable string."""
    args = exc.args[0] if exc.args else exc
    return str(args)


def _minimal_valid(tmp_path: Path, *, simulate: bool = True) -> dict:
    """
    Smallest setting set that should pass validation in simulate mode
    (readable prompt file, simulate=True, no base_url required).
    """
    prompt = tmp_path / "prompt.toml"
    prompt.write_text("[system]\ninstruction = 'x'\n", encoding="utf-8")

    s = _blank_settings()
    s["simulate_bool_setting"].value = simulate
    s["prompt_file_path_setting"].value = prompt
    s["base_directory_path_setting"].value = tmp_path
    if not simulate:
        s["base_url_string_setting"].value = "http://localhost:11434/v1"
    return s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConfigurationValidator:
    def test_missing_prompt_and_task_raises(self, tmp_path: Path) -> None:
        """Either a prompt file or a non-empty task is mandatory."""
        s = _blank_settings()
        s["simulate_bool_setting"].value = True
        s["base_directory_path_setting"].value = tmp_path

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "prompt" in msg.lower() or "mandatory" in msg.lower()

    def test_invalid_output_mode_raises(self, tmp_path: Path) -> None:
        s = _minimal_valid(tmp_path)
        s["output_mode_string_setting"].value = "z"  # not in {a, w, x}

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert (
            "output_mode" in msg.lower()
            or "append" in msg.lower()
            or "exclusive" in msg.lower()
        )

    def test_retry_delay_out_of_range_raises(self, tmp_path: Path) -> None:
        s = _minimal_valid(tmp_path)
        s["retry_delay_int_setting"].value = 21  # hard upper bound is 20

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "retry_delay" in msg.lower() or "20" in msg

    def test_chars_per_token_must_be_positive(self, tmp_path: Path) -> None:
        s = _minimal_valid(tmp_path)
        s["chars_per_token_float_setting"].value = 0.0

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "chars_per_token" in msg.lower() or "0.0" in msg

    def test_simulate_mode_does_not_require_base_url(self, tmp_path: Path) -> None:
        """In simulate mode the LLM endpoint is optional."""
        s = _minimal_valid(tmp_path, simulate=True)
        # deliberately leave base_url unset

        result = ConfigurationValidator().run(**s)

        assert result  # non-empty list of checked elements
        assert s["output_mode_string_setting"].value == "x"  # default applied

    def test_non_simulate_requires_base_url(self, tmp_path: Path) -> None:
        s = _minimal_valid(tmp_path, simulate=False)
        # wipe base_url if the helper set it
        s["base_url_string_setting"] = BaseURLStringSetting(_key="base_url")

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "base_url" in msg.lower() or "llm" in msg.lower()

    def test_client_key_without_cert_raises(self, tmp_path: Path) -> None:
        key = tmp_path / "client.key"
        key.write_text("dummy-key", encoding="utf-8")

        s = _minimal_valid(tmp_path)
        s["client_key_file_path_setting"].value = key
        # client_cert deliberately unset

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "client_key" in msg.lower() or "client_cert" in msg.lower()
