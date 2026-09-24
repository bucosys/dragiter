# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Unit tests for ConfigurationValidator.

These tests exercise the mandatory-field rules, range checks and the
simulate-mode exception for base_url — the rules that decide whether a
run is allowed to start at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from support import blank_parameter_groups

from dragiter.application.config.configuration_validator import (
    ConfigurationValidator,
    ConfigurationValidatorError,
)
from dragiter.domain.models.settings import ValueOrigin

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
        """Either a prompt file or a non-empty task is mandatory.

        Covers CONF-24.
        """
        s = _blank_settings()
        s["ep"].simulate_bool_setting.set(True, ValueOrigin.CLI)
        s["wp"].base_directory_path_setting.set(tmp_path, ValueOrigin.CLI)
        s["op"].output_mode_string_setting.set("x", ValueOrigin.DEFAULT)

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "prompt" in msg.lower() or "mandatory" in msg.lower()

    def test_invalid_output_mode_raises(self, tmp_path: Path) -> None:
        """Covers CONF-25."""
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
        """Covers CONF-26."""
        s = _minimal_valid(tmp_path)
        s["aisp"].retry_delay_int_setting.set(21, ValueOrigin.CLI)  # hard upper bound is 20

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "retry_delay" in msg.lower() or "20" in msg

    def test_chars_per_token_must_be_positive(self, tmp_path: Path) -> None:
        """Covers CONF-27."""
        s = _minimal_valid(tmp_path)
        s["aisp"].chars_per_token_float_setting.set(0.0, ValueOrigin.CLI)

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "chars_per_token" in msg.lower() or "0.0" in msg

    def test_simulate_mode_does_not_require_base_url(self, tmp_path: Path) -> None:
        """In simulate mode the LLM endpoint is optional.

        Covers CONF-28.
        """
        s = _minimal_valid(tmp_path, simulate=True)
        # deliberately leave base_url unset

        result = ConfigurationValidator().run(**s)

        assert result is None
        assert s["op"].output_mode_string_setting.value == "x"

    def test_non_simulate_requires_base_url(self, tmp_path: Path) -> None:
        """Covers CONF-29."""
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
        """Covers CONF-30."""
        key = tmp_path / "client.key"
        key.write_text("dummy-key", encoding="utf-8")

        s = _minimal_valid(tmp_path)
        s["aisp"].client_key_file_path_setting.set(key, ValueOrigin.CLI)
        # client_cert deliberately unset

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "client_key" in msg.lower() or "client_cert" in msg.lower()

    def test_pack_limit_chars_negative_raises(self, tmp_path: Path) -> None:
        """Covers CONF-31."""
        s = _minimal_valid(tmp_path)
        s["ep"].pack_limit_chars_int_setting.set(-1, ValueOrigin.CLI)

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "pack_limit_chars" in msg.lower()

    def test_pack_limit_chars_zero_is_accepted(self, tmp_path: Path) -> None:
        s = _minimal_valid(tmp_path)
        s["ep"].pack_limit_chars_int_setting.set(0, ValueOrigin.CLI)

        result = ConfigurationValidator().run(**s)

        assert result is None

    def test_max_chunks_zero_raises(self, tmp_path: Path) -> None:
        """Covers CONF-32."""
        s = _minimal_valid(tmp_path)
        s["ep"].max_chunks_int_setting.set(0, ValueOrigin.CLI)

        with pytest.raises(ConfigurationValidatorError) as exc_info:
            ConfigurationValidator().run(**s)

        msg = _findings(exc_info.value)
        assert "max_chunks" in msg.lower()

    def test_max_chunks_positive_is_accepted(self, tmp_path: Path) -> None:
        s = _minimal_valid(tmp_path)
        s["ep"].max_chunks_int_setting.set(400, ValueOrigin.CLI)

        result = ConfigurationValidator().run(**s)

        assert result is None
