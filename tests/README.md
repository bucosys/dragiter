# Tests for dragiter

This directory contains unit, security, and end-to-end tests for the dragiter CLI tool.

The tests are **not** included in the installed wheel. They ship only with the
source distribution (sdist) and the Git repository.

## Prerequisites

- Python >= 3.11
- pytest (`pip install pytest` or install the project with the `dev` extra)

## How to run the tests

### From a cloned repository or unpacked source tree

```bash
pip install -e ".[dev]"   # installs dragiter + pytest in editable mode
pytest -q
# or
python -m pytest
```

### From a published source distribution

```bash
pip download dragiter --no-binary=:all: -d .
tar xf dragiter-*.tar.gz
cd dragiter-*/
pip install -e ".[dev]"
pytest -q
```

## Notes

- Most tests run without API keys or a live LLM.
- Optional integration tests (e.g. local Ollama, Caddy TLS/mTLS) are skipped
  automatically when the required service is not available.
- New tests should follow the naming convention `test_*.py` and live directly
  under `tests/`.
