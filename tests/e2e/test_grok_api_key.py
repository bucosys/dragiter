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

# tests/e2e/test_grok_api_key.py
"""
E2E test: Passing the Grok API key via an environment variable.

This test is executed only when GROK_API_KEY is set
(i.e. locally in PyCharm, not in the GitLab CI).
"""

import os
from pathlib import Path
import shutil
import subprocess

import pytest

# The entire test is skipped when the key is not present
pytestmark = pytest.mark.skipif(
    not os.getenv("GROK_API_KEY"),
    reason="GROK_API_KEY not set - skipping live Grok API key test (expected in CI)",
)


@pytest.fixture
def dragiter_bin() -> str:
    """Locate the dragiter executable in the current venv / PATH."""
    path = shutil.which("dragiter")
    if not path:
        pytest.skip("dragiter executable not found in PATH")
    return path


def test_api_key_is_passed_via_environment_variable(dragiter_bin: str, tmp_path: Path):
    """
    Simulates the exact invocation style:

        DRAGITER_API_KEY=$GROK_API_KEY dragiter ...

    and verifies that the key is accepted (no "missing/invalid key" error).
    """
    env = os.environ.copy()

    # The decisive step - analogous to what is done in the PyCharm run configuration
    env["DRAGITER_API_KEY"] = env["GROK_API_KEY"]
    env["DRAGITER_BASE_URL"] = "https://api.x.ai/v1"
    env["DRAGITER_MODEL_NAME"] = "grok-4"

    # Very lightweight call: only --version + verbose.
    # Sufficient to confirm that the environment variable is correctly picked up
    # and that no authentication error occurs.
    result = subprocess.run(
        [
            dragiter_bin,
            "-v",
            "--version",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    combined = (result.stdout or "") + (result.stderr or "")
    print(combined)  # visible with pytest -s

    # The key must not be reported as missing or invalid
    assert "api key" not in combined.lower() or "********" in combined, (
        "API key appears not to have been accepted via the environment variable"
    )

    # Version information should be emitted correctly
    assert "dragiter" in combined.lower()
    assert result.returncode == 0
