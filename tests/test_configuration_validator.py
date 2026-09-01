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
from dragiter.domain.models.settings import ValueOrigin
from tests.support import blank_parameter_groups

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _blank_settings() -> dict:
    """Fresh, unset parameter groups matching ConfigurationValidator.run()."""
    return blank_parameter_groups()


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
    s["ep"].simulate_bool_setting.set(simulate, ValueOrigin.CLI)
    s["ip"].prompt_file_path_setting.set(prompt, ValueOrigin.CLI)
    s["wp"].base_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
    s["op"].output_mode_string_setting.set("x", ValueOrigin.DEFAULT)
    if not simulate:
        s["aisp"].base_url_string_setting.set(
            "http://localhost:11434/v1", ValueOrigin.CLI
        )
    return s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConfigurationValidator:
    def test_missing_prompt_and_task_raises(self, tmp_path: Path) -> None:
        """Either a prompt file or a non-empty task is mandatory."""
        s = _blank_settings()
        s["ep"].simulate_bool_setting.set(True, ValueOrigin.CLI)
        s["wp"].base_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
        s["op"].output_mode_string_setting.set("x", ValueOrigin.DEFAULT)

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "prompt" in msg.lower() or "mandatory" in msg.lower()

    def test_invalid_output_mode_raises(self, tmp_path: Path) -> None:
        s = _blank_settings()
        prompt = tmp_path / "prompt.toml"
        prompt.write_text("[system]\ninstruction = 'x'\n", encoding="utf-8")
        s["ep"].simulate_bool_setting.set(True, ValueOrigin.CLI)
        s["ip"].prompt_file_path_setting.set(prompt, ValueOrigin.CLI)
        s["wp"].base_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
        s["op"].output_mode_string_setting.set("z", ValueOrigin.CLI)

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
        s["aisp"].retry_delay_int_setting.set(21, ValueOrigin.CLI)  # hard upper bound is 20

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "retry_delay" in msg.lower() or "20" in msg

    def test_chars_per_token_must_be_positive(self, tmp_path: Path) -> None:
        s = _minimal_valid(tmp_path)
        s["aisp"].chars_per_token_float_setting.set(0.0, ValueOrigin.CLI)

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "chars_per_token" in msg.lower() or "0.0" in msg

    def test_simulate_mode_does_not_require_base_url(self, tmp_path: Path) -> None:
        """In simulate mode the LLM endpoint is optional."""
        s = _minimal_valid(tmp_path, simulate=True)
        # deliberately leave base_url unset

        result = ConfigurationValidator().run(**s)

        assert result is None
        assert s["op"].output_mode_string_setting.value == "x"

    def test_non_simulate_requires_base_url(self, tmp_path: Path) -> None:
        s = _blank_settings()
        prompt = tmp_path / "prompt.toml"
        prompt.write_text("[system]\ninstruction = 'x'\n", encoding="utf-8")
        s["ep"].simulate_bool_setting.set(False, ValueOrigin.CLI)
        s["ip"].prompt_file_path_setting.set(prompt, ValueOrigin.CLI)
        s["wp"].base_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
        s["op"].output_mode_string_setting.set("x", ValueOrigin.DEFAULT)
        # base_url deliberately unset

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "base_url" in msg.lower() or "llm" in msg.lower()

    def test_client_key_without_cert_raises(self, tmp_path: Path) -> None:
        key = tmp_path / "client.key"
        key.write_text("dummy-key", encoding="utf-8")

        s = _minimal_valid(tmp_path)
        s["aisp"].client_key_file_path_setting.set(key, ValueOrigin.CLI)
        # client_cert deliberately unset

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "client_key" in msg.lower() or "client_cert" in msg.lower()
