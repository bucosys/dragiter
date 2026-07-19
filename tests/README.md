# E2E Tests for dragiter

This directory contains end-to-end tests for the dragiter CLI tool.

## Prerequisites
- dragiter must be installed in the current Python environment (`pip install dragiter` or `pip install -e .` from the project root).
- pytest is recommended: `pip install pytest`

## How to run the tests

After extracting the tests:

```bash
dragiter-gen-tests .
cd tests
pytest -q
# or
python -m pytest