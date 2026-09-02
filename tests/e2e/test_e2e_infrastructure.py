# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
E2E infrastructure tests for the dragiter CLI.

These tests verify that the core command-line interface is reachable
and that basic flags (including simulation mode) are accepted without
unhandled exceptions. They serve as a minimal, self-contained template.
"""

from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from dragiter import __tool_name__, __version__
from dragiter.application.config.configuration_loader import ConfigurationLoader
from dragiter.domain.models.settings import SimulateBoolSetting


def _get_dragiter_command() -> list[str]:
    """Best available way to invoke the installed or in-tree CLI."""
    if shutil.which("dragiter"):
        return ["dragiter"]
    return [sys.executable, "-m", "dragiter.cli"]


def _run_dragiter(args: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    """Helper kept for optional live/functional tests that shell out to the CLI."""
    return subprocess.run(
        _get_dragiter_command() + args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=Path.cwd(),
    )


def test_dragiter_version():
    """Package metadata must expose the tool name and a version string."""
    assert __tool_name__ == "dragiter"
    assert __version__
    assert "2026" in __version__ or __version__[0].isdigit()


def test_dragiter_help(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    """Argparse help must mention the project description."""
    monkeypatch.setattr(sys, "argv", ["dragiter", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        ConfigurationLoader()._get_args()
    assert exc_info.value.code == 0
    assert "Deterministic Context Iterator" in capsys.readouterr().out


def test_dragiter_simulate_flag_accepted(monkeypatch: pytest.MonkeyPatch):
    """The -s / --simulate flag must be recognised by the configuration loader."""
    monkeypatch.setattr(sys, "argv", ["dragiter", "-s"])
    loader = ConfigurationLoader()
    loader._get_args()
    simulate = next(
        item.value_setting_object
        for item in loader.config_values
        if isinstance(item.value_setting_object, SimulateBoolSetting)
    )
    assert simulate.is_set is True
    assert simulate.value is True
