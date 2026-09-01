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
