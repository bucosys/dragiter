# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Tests for ConfigurationLoader's environment-variable handling and its
configuration precedence order (CLI argument > TOML config file >
environment variable), as documented in docs/manual.md, "Mixed
Configuration".

Boolean semantics are unified with LoggingConfigurator:
a value is considered truthy when, after stripping and upper-casing, it is
one of ``TRUE``, ``1`` or ``YES``.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

import pytest
from support import setting_of

from dragiter.application.config.configuration_loader import ConfigurationLoader
from dragiter.domain.models.settings import (
    BaseURLStringSetting,
    CharsPerTokenFloatSetting,
    DebugBoolSetting,
    LogFilePathSetting,
    MaxContextTokensIntSetting,
    MaxRetryIntSetting,
    ModelNameStringSetting,
    TemperatureFloatSetting,
    ValueOrigin,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_name_item(loader: ConfigurationLoader):
    """Return the ArgumentDecorator wrapping ModelNameStringSetting."""
    return next(
        item
        for item in loader.config_values
        if isinstance(item.value_setting_object, ModelNameStringSetting)
    )


def _debug_item(loader: ConfigurationLoader):
    """Return the ArgumentDecorator wrapping DebugBoolSetting."""
    return next(
        item
        for item in loader.config_values
        if isinstance(item.value_setting_object, DebugBoolSetting)
    )


def _max_context_tokens_item(loader: ConfigurationLoader):
    return next(
        item
        for item in loader.config_values
        if isinstance(item.value_setting_object, MaxContextTokensIntSetting)
    )


def _max_retry_item(loader: ConfigurationLoader):
    return next(
        item
        for item in loader.config_values
        if isinstance(item.value_setting_object, MaxRetryIntSetting)
    )


def _chars_per_token_item(loader: ConfigurationLoader):
    return next(
        item
        for item in loader.config_values
        if isinstance(item.value_setting_object, CharsPerTokenFloatSetting)
    )


def _temperature_item(loader: ConfigurationLoader):
    return next(
        item
        for item in loader.config_values
        if isinstance(item.value_setting_object, TemperatureFloatSetting)
    )


def _log_file_item(loader: ConfigurationLoader):
    return next(
        item
        for item in loader.config_values
        if isinstance(item.value_setting_object, LogFilePathSetting)
    )


def _base_url_item(loader: ConfigurationLoader):
    return next(
        item
        for item in loader.config_values
        if isinstance(item.value_setting_object, BaseURLStringSetting)
    )


# ---------------------------------------------------------------------------
# Unit tests: _set_settings_from_environment() in isolation
#
# These call the private method directly (bypassing _get_args() / argparse
# and _set_settings_from_config()) so the env-var logic can be tested without
# any dependency on sys.argv or the filesystem.
# ---------------------------------------------------------------------------

def test_env_var_sets_unset_string_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    """A matching env var is applied to an unset string setting.

    Covers CONF-03.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-model")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.value == "env-model"


def test_env_var_does_not_override_already_set_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env vars must never win over a value that was already set (e.g. by the CLI).

    Covers CONF-01.
    """
    loader = ConfigurationLoader()
    _model_name_item(loader).value_setting_object.set("cli-value", ValueOrigin.CLI)
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-value")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.value == "cli-value"


def test_env_var_string_setting_value_is_stripped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leading/trailing whitespace from the env var value must be stripped.

    Covers CONF-05.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "  padded-value  ")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.value == "  padded-value  "


@pytest.mark.parametrize(
    "value, expected",
    [
        # truthy (unified with LoggingConfigurator)
        ("true", True),
        ("TRUE", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("YES", True),
        ("Yes", True),
        # falsy
        ("false", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("n", False),
    ],
)
def test_env_var_bool_setting_unified_truthy_values(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    """
    After unification both ConfigurationLoader and LoggingConfigurator
    accept the same set of truthy values (case-insensitive):
    "true", "1", "yes".

    Covers CONF-06.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_DEBUG", value)

    loader._set_settings_from_environment()

    assert _debug_item(loader).value_setting_object.value is expected


def test_env_var_bool_setting_true_is_case_insensitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_DEBUG", "TRUE")

    loader._set_settings_from_environment()

    assert _debug_item(loader).value_setting_object.value is True


def test_unrelated_env_var_does_not_affect_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers CONF-04."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("SOME_UNRELATED_VAR", "whatever")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.is_set is False


def test_env_var_uses_documented_uppercase_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Encodes the documented convention, e.g. export DRAGITER_MODEL_NAME=..."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "uppercase-env")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.value == "uppercase-env"


# ---------------------------------------------------------------------------
# Integer and Float settings from environment variables
# ---------------------------------------------------------------------------

def test_env_var_sets_unset_integer_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    """DRAGITER_MAX_CONTEXT_TOKENS must be parsed as int.

    Covers CONF-07.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MAX_CONTEXT_TOKENS", "128000")

    loader._set_settings_from_environment()

    setting = _max_context_tokens_item(loader).value_setting_object
    assert setting.is_set is True
    assert setting.value == 128000
    assert isinstance(setting.value, int)


def test_env_var_sets_unset_float_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    """DRAGITER_CHARS_PER_TOKEN must be parsed as float.

    Covers CONF-08.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_CHARS_PER_TOKEN", "3.8")

    loader._set_settings_from_environment()

    setting = _chars_per_token_item(loader).value_setting_object
    assert setting.is_set is True
    assert setting.value == pytest.approx(3.8)
    assert isinstance(setting.value, float)


def test_env_var_integer_setting_value_is_stripped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leading/trailing whitespace around an integer env value must be stripped."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MAX_RETRY", "  5  ")

    loader._set_settings_from_environment()

    assert _max_retry_item(loader).value_setting_object.value == 5


def test_env_var_float_setting_value_is_stripped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leading/trailing whitespace around a float env value must be stripped."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_TEMPERATURE", "  0.25  ")

    loader._set_settings_from_environment()

    assert _temperature_item(loader).value_setting_object.value == pytest.approx(0.25)


def test_env_var_integer_does_not_override_already_set_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env vars must never win over a value that was already set (e.g. by the CLI)."""
    loader = ConfigurationLoader()
    _max_context_tokens_item(loader).value_setting_object.set(64000, ValueOrigin.CLI)
    monkeypatch.setenv("DRAGITER_MAX_CONTEXT_TOKENS", "128000")

    loader._set_settings_from_environment()

    assert _max_context_tokens_item(loader).value_setting_object.value == 64000


def test_env_var_float_does_not_override_already_set_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader = ConfigurationLoader()
    _temperature_item(loader).value_setting_object.set(0.0, ValueOrigin.CLI)
    monkeypatch.setenv("DRAGITER_TEMPERATURE", "0.9")

    loader._set_settings_from_environment()

    assert _temperature_item(loader).value_setting_object.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# $ variable expansion in environment values
# ---------------------------------------------------------------------------

def test_env_var_dollar_expansion_for_string_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Values that start with $ are expanded via os.path.expandvars before
    assignment. Useful for composing URLs or paths from other env vars.

    Covers CONF-10.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("LLM_HOST", "localhost:11434")
    monkeypatch.setenv("DRAGITER_BASE_URL", "$LLM_HOST/v1")

    loader._set_settings_from_environment()

    assert _base_url_item(loader).value_setting_object.value == "localhost:11434/v1"


def test_env_var_dollar_expansion_for_path_setting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """$ expansion must also work for Path settings (e.g. log file location)."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setenv("MY_LOG_DIR", str(log_dir))
    monkeypatch.setenv("DRAGITER_LOG_FILE", "$MY_LOG_DIR/dragiter.log")

    loader = ConfigurationLoader()
    loader._set_settings_from_environment()

    result = _log_file_item(loader).value_setting_object.value
    assert result == (log_dir / "dragiter.log").resolve()


def test_env_var_dollar_expansion_for_integer_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    $ expansion runs before type conversion, so an intermediate env var
    holding a numeric string can feed an IntegerSetting.

    Covers CONF-12.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("MY_CONTEXT_LIMIT", "32000")
    monkeypatch.setenv("DRAGITER_MAX_CONTEXT_TOKENS", "$MY_CONTEXT_LIMIT")

    loader._set_settings_from_environment()

    assert _max_context_tokens_item(loader).value_setting_object.value == 32000


def test_env_var_dollar_expansion_for_float_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader = ConfigurationLoader()
    monkeypatch.setenv("MY_TEMP", "0.15")
    monkeypatch.setenv("DRAGITER_TEMPERATURE", "$MY_TEMP")

    loader._set_settings_from_environment()

    assert _temperature_item(loader).value_setting_object.value == pytest.approx(0.15)


def test_env_var_unresolved_dollar_reference_is_kept_as_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    If a $-reference cannot be resolved, expandvars leaves it unchanged
    and the raw string is assigned (for StringSetting).

    Covers CONF-11.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_BASE_URL", "$THIS_VAR_DOES_NOT_EXIST/v1")

    loader._set_settings_from_environment()

    # os.path.expandvars leaves unknown $VAR references intact
    assert (
        _base_url_item(loader).value_setting_object.value
        == "$THIS_VAR_DOES_NOT_EXIST/v1"
    )


# ---------------------------------------------------------------------------
# Integration tests: full precedence chain via the public run() method
#
# docs/manual.md, "Mixed Configuration":
#   1. Command-line arguments
#   2. TOML configuration file
#   3. Environment variables
#
# Path.home() is patched to an isolated tmp_path for every test in this
# section so a real ~/.config/dragiter/config.toml on the machine running
# the tests can never leak in and make these tests flaky/environment-dependent.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolated_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def test_cli_argument_wins_over_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers CONF-01."""
    monkeypatch.setattr(sys, "argv", ["dragiter", "--model-name", "cli-value"])
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-value")

    settings = ConfigurationLoader().run()

    model_setting = setting_of(settings, ModelNameStringSetting)
    assert model_setting.value == "cli-value"


def test_cli_api_key_is_masked_in_debug_log(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Covers CONF-33."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["dragiter", "--api-key", "sk-supersecret123", "--model-name", "gpt-visible"],
    )
    with caplog.at_level(logging.DEBUG):
        ConfigurationLoader().run()

    assert "sk-supersecret123" not in caplog.text
    assert "********" in caplog.text
    # A non-key setting must still be logged in full, proving this isn't just
    # blanket-suppressed debug logging.
    assert "gpt-visible" in caplog.text


def test_config_file_wins_over_environment_variable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Covers CONF-02."""
    config_path = tmp_path / "test-config.toml"
    config_path.write_text('model_name = "config-file-value"\n')

    monkeypatch.setattr(sys, "argv", ["dragiter", "-c", str(config_path)])
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-value")

    settings = ConfigurationLoader().run()

    model_setting = setting_of(settings, ModelNameStringSetting)
    assert model_setting.value == "config-file-value"


def test_environment_variable_applies_when_nothing_else_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers CONF-03, CONF-18 (no -c, no default config file, run proceeds)."""
    monkeypatch.setattr(sys, "argv", ["dragiter"])
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-only-value")

    settings = ConfigurationLoader().run()

    model_setting = setting_of(settings, ModelNameStringSetting)
    assert model_setting.value == "env-only-value"


def test_cli_config_path_wins_over_config_file_env_var(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """-c PATH is used regardless of $DRAGITER_CONFIG_FILE pointing elsewhere.

    Covers CONF-17.
    """
    cli_config = tmp_path / "cli-config.toml"
    cli_config.write_text('model_name = "from-cli-config"\n')
    env_config = tmp_path / "env-config.toml"
    env_config.write_text('model_name = "from-env-config"\n')

    monkeypatch.setattr(sys, "argv", ["dragiter", "-c", str(cli_config)])
    monkeypatch.setenv("DRAGITER_CONFIG_FILE", str(env_config))

    settings = ConfigurationLoader().run()

    model_setting = setting_of(settings, ModelNameStringSetting)
    assert model_setting.value == "from-cli-config"
