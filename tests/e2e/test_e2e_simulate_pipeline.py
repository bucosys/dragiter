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
End-to-end simulation-mode pipeline test.

Runs the full CLI path (config → resources → chunks → loop → mock LLM →
output) without any network access. This is the highest-ROI integration
check: unit tests can be green while the wiring between pipeline workers
is broken.
"""

from __future__ import annotations

import json
from pathlib import Path

from test_e2e_infrastructure import _run_dragiter


def test_simulate_pipeline_writes_mock_output(tiny_example_dir: Path) -> None:
    """
    Full simulate run against the self-contained tiny fixtures.

    Expectations:
      * exit code 0
      * no unhandled traceback
      * at least one output file under -O
      * every output file contains a MockAI payload ("mock": true)
    """
    output_dir = tiny_example_dir / "outputs" / "simulate_e2e"
    output_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-s",
        "-v",
        "-b",
        str(tiny_example_dir),
        "-p",
        str(tiny_example_dir / "01_tiny_prompt.toml"),
        "-r",
        str(tiny_example_dir / "01_tiny_resource.toml"),
        "-l",
        str(tiny_example_dir / "01_tiny_loop.txt"),
        "-O",
        str(output_dir),
        "-m",
        "w",
    ]

    result = _run_dragiter(flags, timeout=60)

    assert result.returncode == 0, (
        f"Simulate pipeline failed (exit {result.returncode}).\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert "Traceback (most recent call last)" not in result.stderr

    created = [p for p in output_dir.rglob("*") if p.is_file()]
    assert created, f"No output files written to {output_dir}"

    for path in created:
        text = path.read_text(encoding="utf-8")
        # MockAIService writes a JSON object with "mock": true
        assert '"mock"' in text or "'mock'" in text, (
            f"Output {path.name} does not look like a MockAI payload:\n{text[:400]}"
        )


def test_simulate_pipeline_with_activity_log(tiny_example_dir: Path) -> None:
    """
    Same pipeline plus activity JSONL — verifies the audit path is wired.
    """
    output_dir = tiny_example_dir / "outputs" / "simulate_e2e_activity"
    output_dir.mkdir(parents=True, exist_ok=True)
    activity_file = tiny_example_dir / "activity_simulate.jsonl"

    flags = [
        "-s",
        "-b",
        str(tiny_example_dir),
        "-p",
        str(tiny_example_dir / "01_tiny_prompt.toml"),
        "-r",
        str(tiny_example_dir / "01_tiny_resource.toml"),
        "-l",
        str(tiny_example_dir / "01_tiny_loop.txt"),
        "-O",
        str(output_dir),
        "-m",
        "w",
        "-a",
        str(activity_file),
    ]

    result = _run_dragiter(flags, timeout=60)
    assert result.returncode == 0, (
        f"Simulate pipeline with activity log failed (exit {result.returncode}).\n"
        f"--- stderr ---\n{result.stderr}"
    )

    assert activity_file.is_file(), "Activity file was not created"
    lines = [
        line
        for line in activity_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 2, "Activity log should contain several records"

    # Each line must be valid JSON (JSONL integrity)
    for line in lines:
        json.loads(line)
