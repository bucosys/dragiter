"""
Shared pytest configuration for all tests.
Ensures common directories like outputs/ are available.
"""

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "tests" / "outputs"


@pytest.fixture(scope="session", autouse=True)
def ensure_outputs_directory():
    """Automatically create the outputs directory for all functional tests."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Global outputs directory ready for inspection: {OUTPUTS_DIR}")
    return OUTPUTS_DIR