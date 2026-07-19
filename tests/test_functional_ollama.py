"""
Functional / Integration tests with real LLM (Ollama).

- Uses temporary directories for automatic test runs (clean)
- Writes a copy to tests/outputs/ for manual inspection
"""
import subprocess
import tempfile
import shutil
from pathlib import Path

import pytest

from tests.test_e2e_infrastructure import _run_dragiter


def ollama_is_available() -> bool:
    """Check if Ollama is running and has at least one model."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and "NAME" in result.stdout
    except Exception:
        return False


PROJECT_ROOT = Path(__file__).parent.parent
TINY_EXAMPLE_DIR = PROJECT_ROOT / "examples" / "04_tiny_functional_test"
OUTPUTS_DIR = PROJECT_ROOT / "tests" / "outputs"


@pytest.mark.skipif(not ollama_is_available(), reason="Ollama not available")
def test_functional_ollama_tiny_workflow(ensure_outputs_directory):
    """Basic functional test – outputs go to temp + manual inspection folder."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_output_dir = Path(tmp_dir) / "output"
        temp_output_dir.mkdir()

        flags = [
            "-v",
            "-c", str(PROJECT_ROOT / "tests" / "configs" / "config-ollama.toml"),
            "-p", str(TINY_EXAMPLE_DIR / "04_tiny_prompt.toml"),
            "-r", str(TINY_EXAMPLE_DIR / "04_tiny_resource.toml"),
            "-l", str(TINY_EXAMPLE_DIR / "04_tiny_loop.txt"),
            "-O", str(temp_output_dir),
            "--base-directory", str(TINY_EXAMPLE_DIR),
        ]

        result = _run_dragiter(flags, timeout=90)

        assert result.returncode == 0, f"Test failed: {result.stderr}"

        # Copy results to manual inspection folder
        manual_dir = OUTPUTS_DIR / "tiny_ollama"
        manual_dir.mkdir(parents=True, exist_ok=True)
        for file in temp_output_dir.glob("**/*"):
            if file.is_file():
                shutil.copy2(file, manual_dir / file.name)

        created_files = list(manual_dir.glob("**/*.md"))
        assert len(created_files) > 0, "No output files were created"

        print(f"✅ Tiny Ollama workflow test passed. Results copied to: {manual_dir}")


@pytest.mark.skipif(not ollama_is_available(), reason="Ollama not available")
def test_functional_ollama_tiny_activity_log(ensure_outputs_directory):
    """Test activity logging – activity file in outputs folder for inspection."""
    activity_file = OUTPUTS_DIR / "tiny_activity_ollama.jsonl"

    flags = [
        "-v",
        "-c", str(PROJECT_ROOT / "tests" / "configs" / "config-ollama.toml"),
        "-p", str(TINY_EXAMPLE_DIR / "04_tiny_prompt.toml"),
        "-r", str(TINY_EXAMPLE_DIR / "04_tiny_resource.toml"),
        "-l", str(TINY_EXAMPLE_DIR / "04_tiny_loop.txt"),
        "-a", str(activity_file),
        "--base-directory", str(TINY_EXAMPLE_DIR),
    ]

    result = _run_dragiter(flags, timeout=90)

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert activity_file.exists(), "Activity log was not created"

    content = activity_file.read_text(encoding="utf-8")
    assert len(content.strip()) > 100, "Activity log seems too small"
    assert "***MASKED***" in content or "********" in content, "API key not masked"

    print(f"✅ Tiny Ollama activity log test passed. Log at: {activity_file}")