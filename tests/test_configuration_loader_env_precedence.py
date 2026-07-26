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

"""
Tests for ConfigurationLoader's environment-variable handling and its
configuration precedence order (CLI argument > TOML config file >
environment variable), as documented in docs/manual.md, "Mixed
Configuration".

Regression context:
docs/manual.md and docs/info.txt consistently document environment
variables using a fully upper-cased prefix, e.g. `DRAGITER_MODEL_NAME`.
The actual implementation in `ConfigurationLoader._set_settings_from_environment()`
builds the variable name as:

    env_key = "dragiter_" + item.long_key.upper()

i.e. a *lower-case* "dragiter_" prefix plus an upper-case field name
(e.g. "dragiter_MODEL_NAME"), not the documented "DRAGITER_MODEL_NAME".
Since environment variable names are case-sensitive on Linux/macOS, anyone
following the manual literally (`export DRAGITER_MODEL_NAME=...`) has that
setting silently ignored.

test_env_var_uses_documented_uppercase_prefix() below encodes the
*documented* (intended) behaviour and is marked `xfail(strict=True)`
against today's implementation: it fails now, exactly as expected, and
will start reporting XPASS (which pytest treats as a failure under
strict=True) the moment someone fixes the casing in `configuration_loader.py`
-- at which point the xfail marker should simply be removed.

The remaining tests document/guard the actual, current behaviour of the
env-var and precedence logic so this area of the code has *some* coverage
regardless of how/when the casing bug gets fixed.
"""

import sys
from pathlib import Path

import pytest

from dragiter.application.config.configuration_loader import ConfigurationLoader
from dragiter.domain.models.settings import (
    DebugBoolSetting,
    ModelNameStringSetting,
    MaxContextTokensIntSetting,
    MaxRetryIntSetting,
    CharsPerTokenFloatSetting,
    TemperatureFloatSetting,
    LogFilePathSetting,
    BaseURLStringSetting,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_name_item(loader: ConfigurationLoader):
    """Return the ArgumentDecorator wrapping ModelNameStringSetting for a fresh loader."""
    return next(
        item for item in loader.config_values
        if isinstance(item.value_setting_object, ModelNameStringSetting)
    )


def _debug_item(loader: ConfigurationLoader):
    """Return the ArgumentDecorator wrapping DebugBoolSetting for a fresh loader."""
    return next(
        item for item in loader.config_values
        if isinstance(item.value_setting_object, DebugBoolSetting)
    )


def _max_context_tokens_item(loader: ConfigurationLoader):
    return next(
        item for item in loader.config_values
        if isinstance(item.value_setting_object, MaxContextTokensIntSetting)
    )


def _max_retry_item(loader: ConfigurationLoader):
    return next(
        item for item in loader.config_values
        if isinstance(item.value_setting_object, MaxRetryIntSetting)
    )


def _chars_per_token_item(loader: ConfigurationLoader):
    return next(
        item for item in loader.config_values
        if isinstance(item.value_setting_object, CharsPerTokenFloatSetting)
    )


def _temperature_item(loader: ConfigurationLoader):
    return next(
        item for item in loader.config_values
        if isinstance(item.value_setting_object, TemperatureFloatSetting)
    )


def _log_file_item(loader: ConfigurationLoader):
    return next(
        item for item in loader.config_values
        if isinstance(item.value_setting_object, LogFilePathSetting)
    )


def _base_url_item(loader: ConfigurationLoader):
    return next(
        item for item in loader.config_values
        if isinstance(item.value_setting_object, BaseURLStringSetting)
    )


# ---------------------------------------------------------------------------
# Unit tests: _set_settings_from_environment() in isolation
#
# These call the private method directly (bypassing _get_args() / argparse
# and _set_settings_from_config()) so the env-var logic can be tested without
# any dependency on sys.argv or the filesystem.
# ---------------------------------------------------------------------------

def test_env_var_sets_unset_string_setting(monkeypatch):
    """A matching env var (today's actual 'DRAGITER_' + UPPER convention) is applied."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-model")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.value == "env-model"


def test_env_var_does_not_override_already_set_setting(monkeypatch):
    """Env vars must never win over a value that was already set (e.g. by the CLI)."""
    loader = ConfigurationLoader()
    _model_name_item(loader).value_setting_object.value = "cli-value"
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-value")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.value == "cli-value"


def test_env_var_string_setting_value_is_stripped(monkeypatch):
    """Leading/trailing whitespace from the env var value must be stripped."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "  padded-value  ")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.value == "padded-value"


def test_env_var_bool_setting_accepts_only_literal_true(monkeypatch):
    """
    Current (somewhat surprising) behaviour: only the literal string "true"
    (any case) is treated as truthy. "1" and "yes" evaluate to False.

    Note this is inconsistent with LoggingConfigurator.parse_and_configure(),
    which separately accepts "TRUE", "1", and "YES" for its own DEBUG/VERBOSE
    env vars. This test documents ConfigurationLoader's actual behaviour so a
    future alignment of the two is a deliberate change, not an accident.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_DEBUG", "1")

    loader._set_settings_from_environment()

    assert _debug_item(loader).value_setting_object.value is False


def test_env_var_bool_setting_true_is_case_insensitive(monkeypatch):
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_DEBUG", "TRUE")

    loader._set_settings_from_environment()

    assert _debug_item(loader).value_setting_object.value is True


def test_unrelated_env_var_does_not_affect_settings(monkeypatch):
    loader = ConfigurationLoader()
    monkeypatch.setenv("SOME_UNRELATED_VAR", "whatever")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.is_set is False


def test_env_var_uses_documented_uppercase_prefix(monkeypatch):
    """Encodes the *documented* convention from docs/manual.md, e.g.:

        export DRAGITER_MODEL_NAME="qwen3:8b"
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "uppercase-env")

    loader._set_settings_from_environment()

    assert _model_name_item(loader).value_setting_object.value == "uppercase-env"


# ---------------------------------------------------------------------------
# Integer and Float settings from environment variables
# ---------------------------------------------------------------------------

def test_env_var_sets_unset_integer_setting(monkeypatch):
    """DRAGITER_MAX_CONTEXT_TOKENS must be parsed as int."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MAX_CONTEXT_TOKENS", "128000")

    loader._set_settings_from_environment()

    setting = _max_context_tokens_item(loader).value_setting_object
    assert setting.is_set is True
    assert setting.value == 128000
    assert isinstance(setting.value, int)


def test_env_var_sets_unset_float_setting(monkeypatch):
    """DRAGITER_CHARS_PER_TOKEN must be parsed as float."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_CHARS_PER_TOKEN", "3.8")

    loader._set_settings_from_environment()

    setting = _chars_per_token_item(loader).value_setting_object
    assert setting.is_set is True
    assert setting.value == pytest.approx(3.8)
    assert isinstance(setting.value, float)


def test_env_var_integer_setting_value_is_stripped(monkeypatch):
    """Leading/trailing whitespace around an integer env value must be stripped."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_MAX_RETRY", "  5  ")

    loader._set_settings_from_environment()

    assert _max_retry_item(loader).value_setting_object.value == 5


def test_env_var_float_setting_value_is_stripped(monkeypatch):
    """Leading/trailing whitespace around a float env value must be stripped."""
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_TEMPERATURE", "  0.25  ")

    loader._set_settings_from_environment()

    assert _temperature_item(loader).value_setting_object.value == pytest.approx(0.25)


def test_env_var_integer_does_not_override_already_set_setting(monkeypatch):
    """Env vars must never win over a value that was already set (e.g. by the CLI)."""
    loader = ConfigurationLoader()
    _max_context_tokens_item(loader).value_setting_object.value = 64000
    monkeypatch.setenv("DRAGITER_MAX_CONTEXT_TOKENS", "128000")

    loader._set_settings_from_environment()

    assert _max_context_tokens_item(loader).value_setting_object.value == 64000


def test_env_var_float_does_not_override_already_set_setting(monkeypatch):
    loader = ConfigurationLoader()
    _temperature_item(loader).value_setting_object.value = 0.0
    monkeypatch.setenv("DRAGITER_TEMPERATURE", "0.9")

    loader._set_settings_from_environment()

    assert _temperature_item(loader).value_setting_object.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# $ variable expansion in environment values
# ---------------------------------------------------------------------------

def test_env_var_dollar_expansion_for_string_setting(monkeypatch):
    """
    Values that start with $ are expanded via os.path.expandvars before
    assignment. Useful for composing URLs or paths from other env vars.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("LLM_HOST", "localhost:11434")
    monkeypatch.setenv("DRAGITER_BASE_URL", "$LLM_HOST/v1")

    loader._set_settings_from_environment()

    assert _base_url_item(loader).value_setting_object.value == "localhost:11434/v1"


def test_env_var_dollar_expansion_for_path_setting(monkeypatch, tmp_path):
    """$ expansion must also work for Path settings (e.g. log file location)."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setenv("MY_LOG_DIR", str(log_dir))
    monkeypatch.setenv("DRAGITER_LOG_FILE", "$MY_LOG_DIR/dragiter.log")

    loader = ConfigurationLoader()
    loader._set_settings_from_environment()

    result = _log_file_item(loader).value_setting_object.value
    assert result == (log_dir / "dragiter.log").resolve()


def test_env_var_dollar_expansion_for_integer_setting(monkeypatch):
    """
    $ expansion runs before type conversion, so an intermediate env var
    holding a numeric string can feed an IntegerSetting.
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("MY_CONTEXT_LIMIT", "32000")
    monkeypatch.setenv("DRAGITER_MAX_CONTEXT_TOKENS", "$MY_CONTEXT_LIMIT")

    loader._set_settings_from_environment()

    assert _max_context_tokens_item(loader).value_setting_object.value == 32000


def test_env_var_dollar_expansion_for_float_setting(monkeypatch):
    loader = ConfigurationLoader()
    monkeypatch.setenv("MY_TEMP", "0.15")
    monkeypatch.setenv("DRAGITER_TEMPERATURE", "$MY_TEMP")

    loader._set_settings_from_environment()

    assert _temperature_item(loader).value_setting_object.value == pytest.approx(0.15)


def test_env_var_unresolved_dollar_reference_is_kept_as_is(monkeypatch):
    """
    If a $-reference cannot be resolved, expandvars leaves it unchanged
    and the raw string is assigned (for StringSetting).
    """
    loader = ConfigurationLoader()
    monkeypatch.setenv("DRAGITER_BASE_URL", "$THIS_VAR_DOES_NOT_EXIST/v1")

    loader._set_settings_from_environment()

    # os.path.expandvars leaves unknown $VAR references intact
    assert _base_url_item(loader).value_setting_object.value == "$THIS_VAR_DOES_NOT_EXIST/v1"


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
def _isolated_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def test_cli_argument_wins_over_environment_variable(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["dragiter", "--model-name", "cli-value"])
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-value")

    settings = ConfigurationLoader().run()

    model_setting = next(s for s in settings if isinstance(s, ModelNameStringSetting))
    assert model_setting.value == "cli-value"


def test_config_file_wins_over_environment_variable(monkeypatch, tmp_path):
    config_path = tmp_path / "test-config.toml"
    config_path.write_text('model_name = "config-file-value"\n')

    monkeypatch.setattr(sys, "argv", ["dragiter", "-c", str(config_path)])
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-value")

    settings = ConfigurationLoader().run()

    model_setting = next(s for s in settings if isinstance(s, ModelNameStringSetting))
    assert model_setting.value == "config-file-value"


def test_environment_variable_applies_when_nothing_else_is_set(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["dragiter"])
    monkeypatch.setenv("DRAGITER_MODEL_NAME", "env-only-value")

    settings = ConfigurationLoader().run()

    model_setting = next(s for s in settings if isinstance(s, ModelNameStringSetting))
    assert model_setting.value == "env-only-value"