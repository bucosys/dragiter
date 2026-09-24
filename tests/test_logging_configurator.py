# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""Unit tests for LoggingConfigurator.parse_and_configure().

The boolean semantics are intentionally kept identical to ConfigurationLoader:
a value is considered truthy when, after stripping and upper-casing, it is one
of ``TRUE``, ``1`` or ``YES``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys

import pytest

from dragiter.application.config.logging_configuration import (
    LoggingConfiguration,
    LoggingConfigurator,
)


def _reset_logging() -> None:
    """Remove all handlers so successive tests do not interfere with each other."""
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()


@pytest.fixture(autouse=True)
def clean_logging() -> None:
    """Guarantee a clean logging state before and after every test."""
    _reset_logging()
    yield
    _reset_logging()


def _run(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    env: dict[str, str] | None = None,
) -> LoggingConfiguration:
    """Set argv / environment and invoke the configurator under test."""
    monkeypatch.setattr(sys, "argv", argv)

    # Remove any residual environment variables that could influence the result.
    # We only touch keys that end with the suffixes used by LoggingConfigurator.
    for key in list(os.environ):
        upper = key.upper()
        if upper.endswith(("_DEBUG", "_VERBOSE", "_LOG_FILE", "_BASE_DIRECTORY")):
            monkeypatch.delenv(key, raising=False)

    if env:
        for name, value in env.items():
            monkeypatch.setenv(name, value)

    return LoggingConfigurator.parse_and_configure()


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_default_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """No flags and no environment variables yield WARNING level and no file.

    Covers CONF-19.
    """
    config = _run(monkeypatch, argv=["dragiter"])

    assert config.debug is False
    assert config.verbose is False
    assert config.log_level == logging.WARNING
    assert config.log_file is None


# ---------------------------------------------------------------------------
# CLI flags
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", ["--debug", "-d"])
def test_debug_flag_sets_debug_level(
    monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    """Covers CONF-20."""
    config = _run(monkeypatch, argv=["dragiter", flag])

    assert config.debug is True
    assert config.verbose is False
    assert config.log_level == logging.DEBUG


@pytest.mark.parametrize("flag", ["--verbose", "-v"])
def test_verbose_flag_keeps_warning_level(
    monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    """Covers CONF-21."""
    config = _run(monkeypatch, argv=["dragiter", flag])

    assert config.debug is False
    assert config.verbose is True
    assert config.log_level == logging.WARNING


def test_verbose_without_debug_quiets_httpx2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _run(monkeypatch, argv=["dragiter", "--verbose"])
    assert logging.getLogger("httpx2").level == logging.WARNING


def test_debug_leaves_httpx2_unforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _run(monkeypatch, argv=["dragiter", "--debug"])
    assert logging.getLogger("httpx2").level == logging.NOTSET


def test_debug_takes_precedence_over_verbose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When both flags are present, debug wins and the level becomes DEBUG.

    Covers CONF-22.
    """
    config = _run(monkeypatch, argv=["dragiter", "--debug", "--verbose"])

    assert config.debug is True
    assert config.verbose is True
    assert config.log_level == logging.DEBUG


# ---------------------------------------------------------------------------
# Environment variables - unified boolean semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["true", "TRUE", "True", "1", "yes", "YES", "Yes"],
)
def test_env_debug_accepts_truthy_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Truth values are identical to those accepted by ConfigurationLoader."""
    config = _run(
        monkeypatch,
        argv=["dragiter"],
        env={"DRAGITER_DEBUG": value},
    )

    assert config.debug is True
    assert config.log_level == logging.DEBUG


@pytest.mark.parametrize(
    "value",
    ["false", "0", "no", "off", "", "random"],
)
def test_env_debug_rejects_falsy_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    config = _run(
        monkeypatch,
        argv=["dragiter"],
        env={"DRAGITER_DEBUG": value},
    )

    assert config.debug is False
    assert config.log_level == logging.WARNING


def test_env_verbose_keeps_warning_level(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _run(
        monkeypatch,
        argv=["dragiter"],
        env={"DRAGITER_VERBOSE": "1"},
    )

    assert config.verbose is True
    assert config.debug is False
    assert config.log_level == logging.WARNING


def test_cli_debug_overrides_env_verbose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _run(
        monkeypatch,
        argv=["dragiter", "--debug"],
        env={"DRAGITER_VERBOSE": "true"},
    )

    assert config.debug is True
    assert config.log_level == logging.DEBUG


# ---------------------------------------------------------------------------
# Log-file path resolution
# ---------------------------------------------------------------------------


def test_absolute_log_file_from_cli(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Covers CONF-23."""
    log_path = tmp_path / "absolute.log"
    config = _run(
        monkeypatch,
        argv=["dragiter", "--log-file", str(log_path)],
    )

    assert config.log_file == log_path


def test_relative_log_file_resolved_against_base_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    base = tmp_path / "base"
    base.mkdir()
    config = _run(
        monkeypatch,
        argv=["dragiter", "--base-directory", str(base), "--log-file", "app.log"],
    )

    assert config.log_file == (base / "app.log").resolve()


def test_log_file_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "from-env.log"
    config = _run(
        monkeypatch,
        argv=["dragiter"],
        env={"DRAGITER_LOG_FILE": str(log_path)},
    )

    assert config.log_file == log_path


def test_cli_log_file_takes_precedence_over_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cli_path = tmp_path / "cli.log"
    env_path = tmp_path / "env.log"
    config = _run(
        monkeypatch,
        argv=["dragiter", "--log-file", str(cli_path)],
        env={"DRAGITER_LOG_FILE": str(env_path)},
    )

    assert config.log_file == cli_path


def test_short_flag_L_for_log_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "short.log"
    config = _run(
        monkeypatch,
        argv=["dragiter", "-L", str(log_path)],
    )

    assert config.log_file == log_path
