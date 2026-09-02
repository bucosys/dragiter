# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

# tests/e2e/test_claude_e2e_minimal.py
"""
Minimal E2E test against a live Claude endpoint (via OpenAI-compatible proxy).

- Very low token consumption
- Exactly 3 chunks (assembled into one request per loop item)
- Loop with exactly 2 entries → only 2 LLM calls
- Deterministic, easily validatable answer
- Runs only when CLAUDE_API_KEY is set (locally in PyCharm / CI with secret)

Note:
dragiter uses the OpenAI Python client. Anthropic’s native /v1/messages API is
not OpenAI-compatible. Therefore DRAGITER_BASE_URL must point to a proxy that
exposes an OpenAI-compatible /v1/chat/completions endpoint for Claude models
(LiteLLM, OpenRouter, custom gateway, …).
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

# -------------------------------------------------
# Skip in CI / when the key is absent
# -------------------------------------------------
pytestmark = pytest.mark.skipif(
    not os.getenv("CLAUDE_API_KEY"),
    reason="CLAUDE_API_KEY not set - skipping live Claude E2E test",
)


@pytest.fixture
def dragiter_bin() -> str:
    path = shutil.which("dragiter")
    if not path:
        pytest.skip("dragiter executable not found in PATH")
    return path


@pytest.fixture
def minimal_workspace(tmp_path: Path) -> Path:
    """
    Creates a minimal, self-contained workspace containing:
    - 1 resource file → exactly 3 chunks
    - 1 prompt (token-efficient, temperature=0.0, sequential_processing=false)
    - 1 loop file with exactly 2 entries
    """
    workspace = tmp_path / "e2e_minimal"
    workspace.mkdir()

    # ---------- Resource (split into exactly 3 chunks) ----------
    resource_content = """\
# FACT-A
The secret code for alpha is 42.

# FACT-B
The secret code for beta is 17.

# FACT-C
The secret code for gamma is 99.
"""
    (workspace / "facts.md").write_text(resource_content, encoding="utf-8")

    # Resource definition: chunks by Markdown headings
    resource_toml = """\
[facts]
glob_patterns = ["facts.md"]
regex_pattern = '(^#+\\s+.*$)'
"""
    (workspace / "resource.toml").write_text(resource_toml, encoding="utf-8")

    # ---------- Prompt ----------
    # sequential_processing = false  →  all 3 chunks are assembled into ONE request
    # per loop item  →  only 2 LLM calls in total
    prompt_toml = """\
[system]
instruction = \"\"\"
You are a deterministic extraction engine.
You MUST answer with exactly one line and nothing else.
Never add explanations, punctuation or extra words.
\"\"\"

[task]
first = \"\"\"
Reference material (use only this):
\"\"\"

material = \"\"\"
{CHUNK_CONTENT}
\"\"\"

synthesis = \"\"\"
Question: {LOOP_CONTENT}

From the material above extract the three secret codes in the fixed order alpha, beta, gamma.
Answer with exactly this format and nothing else:

CODES: <alpha>-<beta>-<gamma>
\"\"\"

[behaviour]
temperature = 0.0
sequential_processing = false

[outcome]
output_delimiter = "\\n---\\n"
output_filename_schema = "result_{LOOP_NUM_ID:02d}.txt"
"""
    (workspace / "prompt.toml").write_text(prompt_toml, encoding="utf-8")

    # ---------- Loop (exactly 2 entries) ----------
    loop_content = """\
Extract the codes now.
Confirm the codes again.
"""
    (workspace / "loop.txt").write_text(loop_content, encoding="utf-8")

    return workspace


def test_claude_e2e_minimal_deterministic(dragiter_bin: str, minimal_workspace: Path):
    """
    Live API call against Claude (via OpenAI-compatible endpoint) with minimal token consumption.

    With sequential_processing = false only 2 LLM calls are made
    (one per loop entry, each containing all 3 chunks).

    Expected result (deterministic at temperature=0.0):

        CODES: 42-17-99
    """
    env = os.environ.copy()
    env["DRAGITER_API_KEY"] = env["CLAUDE_API_KEY"]

    # ------------------------------------------------------------------
    # Adjust these two values to your actual OpenAI-compatible Claude endpoint
    # Examples:
    #   - LiteLLM proxy:  http://localhost:4000/v1   + model "claude-sonnet-5"
    #   - OpenRouter:     https://openrouter.ai/api/v1  + model "anthropic/claude-sonnet-5"
    #   - Custom gateway: whatever your infra exposes
    # ------------------------------------------------------------------
    env["DRAGITER_BASE_URL"] = "https://api.anthropic.com/v1"  # ← change if needed
    env["DRAGITER_MODEL_NAME"] = "claude-sonnet-4-6"  # ← change if needed

    output_dir = minimal_workspace / "out"
    output_dir.mkdir()

    result = subprocess.run(
        [
            dragiter_bin,
            "-v",
            "-p",
            "prompt.toml",
            "-r",
            "resource.toml",
            "-l",
            "loop.txt",
            "-O",
            str(output_dir),
        ],
        cwd=minimal_workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )

    print("=== STDOUT ===")
    print(result.stdout)
    print("=== STDERR ===")
    print(result.stderr)

    assert result.returncode == 0, f"dragiter failed with exit code {result.returncode}"

    # sequential_processing = false  →  only 2 result files (one per loop entry)
    result_files = sorted(output_dir.glob("result_*.txt"))
    assert len(result_files) == 2, (
        f"Expected 2 result files (one per loop entry), got {len(result_files)}"
    )

    expected = "CODES: 42-17-99"

    for f in result_files:
        content = f.read_text(encoding="utf-8").strip()
        print(f"--- {f.name} ---\n{content}\n")
        assert expected in content, (
            f"Expected deterministic answer '{expected}' not found in {f.name}.\n"
            f"Got:\n{content}"
        )
