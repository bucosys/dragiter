"""
Functional / Integration tests with real LLM (Ollama).
"""

import subprocess
from pathlib import Path

import pytest

from test_e2e_infrastructure import _run_dragiter


def ollama_is_available() -> bool:
    """Check if Ollama is running and has at least one model."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return result.returncode == 0 and "NAME" in result.stdout
    except Exception:
        return False


@pytest.mark.skipif(not ollama_is_available(), reason="Ollama not available")
def test_functional_ollama_tiny_workflow(tiny_example_dir):
    """Basic functional test using the self-contained tiny fixtures."""
    tests_dir = Path(__file__).parent.resolve()
    config_path = tests_dir / "configs" / "config-ollama.toml"

    # Output lives right next to the copied resources in the same
    # per-test temp tree, no separate outputs fixture required.
    temp_output_dir = tiny_example_dir / "outputs" / "tiny_ollama"
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-v",
        "-c", str(config_path),
        "-p", str(tiny_example_dir / "01_tiny_prompt.toml"),
        "-r", str(tiny_example_dir / "01_tiny_resource.toml"),
        "-l", str(tiny_example_dir / "01_tiny_loop.txt"),
        "-O", str(temp_output_dir),
        "-m", "w",  # overwrite to avoid "file already exists" errors
    ]

    result = _run_dragiter(flags, timeout=360)

    assert result.returncode == 0, f"Test failed: {result.stderr}"

    created_files = list(temp_output_dir.glob("**/*.md"))
    assert len(created_files) > 0, "No output files were created"

    print(f"✅ Tiny Ollama workflow test passed. Results in: {temp_output_dir}")