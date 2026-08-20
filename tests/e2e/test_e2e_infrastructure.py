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


def _get_dragiter_command() -> list[str]:
    """
    Returns the best available way to invoke dragiter.

    1. Prefers the installed console script 'dragiter' if available in PATH.
    2. Falls back to 'python -m dragiter.cli' (works in development / editable installs).
    """
    if shutil.which("dragiter"):
        return ["dragiter"]
    else:
        # Development fallback - does not require __main__.py
        return [sys.executable, "-m", "dragiter.cli"]


def _run_dragiter(args: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    """Helper to invoke dragiter reliably in different environments."""
    cmd = _get_dragiter_command() + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=Path.cwd(),
    )


def test_dragiter_version():
    """The --version flag must succeed and mention the tool or module name.

    When invoked via the console script the output contains 'dragiter'.
    When invoked via ``python -m dragiter.cli`` argparse uses 'cli.py' as prog.
    Both forms are acceptable.
    """
    result = _run_dragiter(["--version"])
    assert result.returncode == 0, (
        f"Unexpected exit code: {result.returncode}\n{result.stderr}"
    )
    stdout_lower = result.stdout.lower()
    assert "dragiter" in stdout_lower or "cli" in stdout_lower, (
        f"Version output should mention 'dragiter' or 'cli', got: {result.stdout!r}"
    )


def test_dragiter_help():
    """The help output must be accessible and contain the project description."""
    result = _run_dragiter(["--help"])
    assert result.returncode == 0, (
        f"Unexpected exit code: {result.returncode}\n{result.stderr}"
    )
    assert "Deterministic Context Iterator" in result.stdout


def test_dragiter_simulate_flag_accepted():
    """
    The -s / --simulate flag must be recognised.

    Even without a full configuration the CLI should not crash with an
    unhandled traceback. A controlled configuration error (return code 1)
    is acceptable for this infrastructure-level check.
    """
    result = _run_dragiter(["-s", "--help"])
    assert result.returncode in (0, 1), (
        f"Unexpected exit code: {result.returncode}\n{result.stderr}"
    )
    assert "Traceback (most recent call last)" not in result.stderr
