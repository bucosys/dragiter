# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Tests for ConfigurationLoader TOML type handling and related edge cases.

Covers stress-test findings 2026-08-13:

  #A  TOML non-string value for StringSetting (e.g. api_key = 12345)
  #B  TOML numeric settings given as strings (e.g. max_context_tokens = "1000")
  #C  Invalid Env integer/float values (e.g. DRAGITER_MAX_CONTEXT_TOKENS=abc)
  #D  TOML simulate = false must set the setting to False (not leave it unset)
  #E  TOML string values for BoolSetting use the unified truthy set
      (TRUE / 1 / YES), identical to environment-variable handling and
      LoggingConfigurator.

Boolean semantics are unified across ConfigurationLoader (TOML + Env) and
LoggingConfigurator.
"""

from __future__ import annotations

import sys

import pytest
from support import flatten_settings

from dragiter.application.config.configuration_loader import (
    ConfigurationLoader,
    ConfigurationLoaderError,
)
from dragiter.domain.models.settings import (
    ApiKeyStringSetting,
    CharsPerTokenFloatSetting,
    DebugBoolSetting,
    MaxContextTokensIntSetting,
    MaxRetryIntSetting,
    ModelNameStringSetting,
    SimulateBoolSetting,
    TemperatureFloatSetting,
    VerboseBoolSetting,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setting(loader: ConfigurationLoader, cls):
    return next(
        item.value_setting_object
        for item in loader.config_values
        if isinstance(item.value_setting_object, cls)
    )


def _run_with_toml(monkeypatch, tmp_path, toml_body: str) -> list:
    """Write toml_body to a temp config, run loader with -c, return flat settings."""
    config_path = tmp_path / "test-config.toml"
    config_path.write_text(toml_body, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dragiter", "-c", str(config_path)])
    return flatten_settings(ConfigurationLoader().run())


def _run_env_only(monkeypatch, env: dict) -> ConfigurationLoader:
    """Fresh loader, only env applied (no CLI args that set values)."""
    monkeypatch.setattr(sys, "argv", ["dragiter"])
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    loader = ConfigurationLoader()
    # Apply env in isolation (same path the full run() uses after CLI/TOML)
    loader._set_settings_from_environment()
    return loader


# ===========================================================================
# Finding #A - StringSetting must accept / convert non-string TOML values
# ===========================================================================

def test_A_toml_int_for_string_setting_is_rejected(monkeypatch, tmp_path):
    """Native TOML integers are not coerced into StringSetting.

    Covers CONF-13.
    """
    with pytest.raises((ConfigurationLoaderError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, "api_key = 12345\n")


def test_A_toml_bool_for_string_setting_is_rejected(monkeypatch, tmp_path):
    """Native TOML booleans are not coerced into StringSetting."""
    with pytest.raises((ConfigurationLoaderError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, "model_name = true\n")


def test_A_toml_normal_string_still_works(monkeypatch, tmp_path):
    """Covers CONF-14."""
    settings = _run_with_toml(monkeypatch, tmp_path, 'api_key = "sk-secret"\n')
    api = next(s for s in settings if isinstance(s, ApiKeyStringSetting))
    assert api.value == "sk-secret"


# ===========================================================================
# Finding #B - Integer/Float settings given as strings in TOML
# ===========================================================================

def test_B_toml_integer_as_string_is_rejected(monkeypatch, tmp_path):
    """Quoted integers stay strings and are rejected by IntegerSetting."""
    with pytest.raises((ConfigurationLoaderError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, 'max_context_tokens = "1000"\n')


def test_B_toml_float_as_string_is_rejected(monkeypatch, tmp_path):
    """Quoted floats stay strings and are rejected by FloatSetting."""
    with pytest.raises((ConfigurationLoaderError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, 'temperature = "0.7"\n')


def test_B_toml_native_integer_still_works(monkeypatch, tmp_path):
    settings = _run_with_toml(monkeypatch, tmp_path, "max_context_tokens = 4096\n")
    s = next(x for x in settings if isinstance(x, MaxContextTokensIntSetting))
    assert s.value == 4096
    assert type(s.value) is int


def test_B_toml_native_float_still_works(monkeypatch, tmp_path):
    settings = _run_with_toml(monkeypatch, tmp_path, "chars_per_token = 3.5\n")
    s = next(x for x in settings if isinstance(x, CharsPerTokenFloatSetting))
    assert s.value == pytest.approx(3.5)
    assert isinstance(s.value, float)


def test_B_toml_invalid_integer_string_raises(monkeypatch, tmp_path):
    """max_context_tokens = "abc" must fail with a clear error, not a late crash."""
    with pytest.raises((ConfigurationLoaderError, ValueError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, 'max_context_tokens = "abc"\n')


def test_B_toml_invalid_float_string_raises(monkeypatch, tmp_path):
    with pytest.raises((ConfigurationLoaderError, ValueError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, 'temperature = "not-a-float"\n')


# ===========================================================================
# Finding #C - Invalid Env integer/float values
# ===========================================================================

def test_C_env_invalid_integer_raises(monkeypatch):
    """
    #C: DRAGITER_MAX_CONTEXT_TOKENS=abc must not be silently ignored
    and must not crash with an opaque error deep in the pipeline.

    Covers CONF-09.
    """
    monkeypatch.setattr(sys, "argv", ["dragiter"])
    monkeypatch.setenv("DRAGITER_MAX_CONTEXT_TOKENS", "abc")
    with pytest.raises((ConfigurationLoaderError, ValueError)):
        ConfigurationLoader().run()


def test_C_env_invalid_float_raises(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["dragiter"])
    monkeypatch.setenv("DRAGITER_TEMPERATURE", "not-a-number")
    with pytest.raises((ConfigurationLoaderError, ValueError)):
        ConfigurationLoader().run()


def test_C_env_valid_integer_is_parsed(monkeypatch):
    loader = _run_env_only(monkeypatch, {"DRAGITER_MAX_CONTEXT_TOKENS": "8192"})
    s = _setting(loader, MaxContextTokensIntSetting)
    assert s.is_set is True
    assert s.value == 8192
    assert type(s.value) is int


def test_C_env_valid_float_is_parsed(monkeypatch):
    loader = _run_env_only(monkeypatch, {"DRAGITER_TEMPERATURE": "0.2"})
    s = _setting(loader, TemperatureFloatSetting)
    assert s.is_set is True
    assert s.value == pytest.approx(0.2)
    assert isinstance(s.value, float)


def test_C_env_integer_with_whitespace_is_stripped(monkeypatch):
    loader = _run_env_only(monkeypatch, {"DRAGITER_MAX_RETRY": "  7  "})
    s = _setting(loader, MaxRetryIntSetting)
    assert s.value == 7


# ===========================================================================
# Finding #D - TOML simulate = false must set False (not leave unset)
# ===========================================================================

def test_D_toml_bool_false_is_set_to_false(monkeypatch, tmp_path):
    """
    #D: simulate = false must result in is_set=True and value=False.
    Previously the setting stayed unset because only truthy values were written.

    Covers CONF-15.
    """
    settings = _run_with_toml(monkeypatch, tmp_path, "simulate = false\n")
    sim = next(s for s in settings if isinstance(s, SimulateBoolSetting))
    assert sim.is_set is True, "simulate=false must set the setting, not leave it unset"
    assert sim.value is False


def test_D_toml_bool_true_is_set_to_true(monkeypatch, tmp_path):
    settings = _run_with_toml(monkeypatch, tmp_path, "simulate = true\n")
    sim = next(s for s in settings if isinstance(s, SimulateBoolSetting))
    assert sim.is_set is True
    assert sim.value is True


def test_D_toml_debug_false_is_set_to_false(monkeypatch, tmp_path):
    settings = _run_with_toml(monkeypatch, tmp_path, "debug = false\n")
    dbg = next(s for s in settings if isinstance(s, DebugBoolSetting))
    assert dbg.is_set is True
    assert dbg.value is False


def test_D_toml_verbose_false_is_set_to_false(monkeypatch, tmp_path):
    settings = _run_with_toml(monkeypatch, tmp_path, "verbose = false\n")
    verb = next(s for s in settings if isinstance(s, VerboseBoolSetting))
    assert verb.is_set is True
    assert verb.value is False


# ===========================================================================
# Finding #E - TOML string values for BoolSetting (unified semantics)
# ===========================================================================

def test_E_toml_string_bool_is_rejected(monkeypatch, tmp_path):
    """Quoted TOML booleans are strings and rejected by BoolSetting.set()."""
    with pytest.raises((ConfigurationLoaderError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, 'simulate = "false"\n')


def test_E_toml_string_true_is_rejected(monkeypatch, tmp_path):
    with pytest.raises((ConfigurationLoaderError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, 'simulate = "true"\n')


def test_E_toml_string_TRUE_is_rejected(monkeypatch, tmp_path):
    with pytest.raises((ConfigurationLoaderError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, 'simulate = "TRUE"\n')


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "false", "0", "no", "off", "", "random"])
def test_E_toml_string_bool_unified_truthy_values(monkeypatch, tmp_path, value: str):
    """Quoted TOML values are not parsed as booleans by the config file path."""
    with pytest.raises((ConfigurationLoaderError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, f'simulate = "{value}"\n')


def test_E_toml_string_false_does_not_become_true(monkeypatch, tmp_path):
    """Quoted debug = \"false\" must not be accepted as a boolean True."""
    with pytest.raises((ConfigurationLoaderError, TypeError)):
        _run_with_toml(monkeypatch, tmp_path, 'debug = "false"\n')


# ===========================================================================
# Combined / precedence sanity
# ===========================================================================

def test_toml_multiple_typed_values_together(monkeypatch, tmp_path):
    """One config file with mixed types must apply all conversions correctly.

    Covers CONF-16.
    """
    body = """
simulate = false
verbose = true
api_key = "42"
max_context_tokens = 2048
temperature = 0.0
model_name = "test-model"
"""
    settings = _run_with_toml(monkeypatch, tmp_path, body)

    sim = next(s for s in settings if isinstance(s, SimulateBoolSetting))
    verb = next(s for s in settings if isinstance(s, VerboseBoolSetting))
    api = next(s for s in settings if isinstance(s, ApiKeyStringSetting))
    ctx = next(s for s in settings if isinstance(s, MaxContextTokensIntSetting))
    temp = next(s for s in settings if isinstance(s, TemperatureFloatSetting))
    model = next(s for s in settings if isinstance(s, ModelNameStringSetting))

    assert sim.value is False and sim.is_set
    assert verb.value is True and verb.is_set
    assert api.value == "42"
    assert ctx.value == 2048 and type(ctx.value) is int
    assert temp.value == pytest.approx(0.0) and isinstance(temp.value, float)
    assert model.value == "test-model"
