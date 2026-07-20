"""
Shared pytest configuration for dragiter.

The tiny functional test data is hosted directly under tests/fixtures/
so that the test suite is completely self-contained.
It works both in the source tree and after `dragiter-gen-tests`.
"""

import shutil
import sys
from pathlib import Path

import pytest

# Ensure tests can import each other
sys.path.insert(0, str(Path(__file__).parent))

TESTS_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = TESTS_DIR.parent.resolve()


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session", autouse=True)
def ensure_outputs_directory() -> Path:
    outputs = TESTS_DIR / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    return outputs


@pytest.fixture(scope="session")
def tiny_example_dir(tmp_path_factory) -> Path:
    """
    Provide a clean copy of the tiny functional test dataset.

    Source of truth is now tests/fixtures/tiny_functional_test/
    (no longer depends on examples/ being present).
    """
    src = TESTS_DIR / "fixtures" / "01_tiny_functional_test"

    if not src.is_dir():
        pytest.fail(
            f"01 Tiny functional test fixtures not found at {src}. "
            "The fixtures directory is required and should be part of the test suite."
        )

    tmp_dir = tmp_path_factory.mktemp("tiny_test")
    target_dir = tmp_dir / "01_tiny_functional_test"

    shutil.copytree(src, target_dir, dirs_exist_ok=True)
    return target_dir