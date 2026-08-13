# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Calendar Versioning](https://calver.org/)
in the form `YYYY.M.D` (with optional pre-release suffixes such as `rc1`, `b1`).

## [Unreleased]

### Added
- MkDocs-based project documentation under `web/` (including index.md with logo and links)
- GitLab CI pipeline: unit tests on Python 3.13 + automatic documentation deployment via GitLab Pages
- Legal Notice (Impressum) and Privacy Policy (English, DDG/MStV compliant)
- Set `site_url` to https://www.dragiter.app/

### Changed
- Complete rewrite of documentation following the Diátaxis framework
  (new Tutorial / How-to / Explanation Manual + separate Technical Reference)
- Polished and rewritten README
- Updated man-page style `info.txt`
- Removed `recurse_symlinks=False` from `Path.glob()` calls
- Relaxed `requires-python` to `>=3.11`
- Updated GitLab CI: copy new Diátaxis docs into MkDocs site and ignore some functional tests
- Rebranding: “Deterministic RAG Iterator” / “modular CLI” → “Deterministic Context Iterator” / “focused CLI”
- Homepage URL updated to https://www.dragiter.app/
- Classifier updated to `Topic :: Scientific/Engineering :: Artificial Intelligence`
- Packaging: include CHANGELOG.md in sdist; exclude `web/` and `site/`
- Unified contact email to `michael.buchold@dragiter.app`
- mkdocs.yml: legal pages in flat navigation (`navigation.sections`)

### Fixed
- Crash on Python < 3.13 caused by the 3.13-only `recurse_symlinks` argument

## [2026.7.26] - 2026-07-26
[https://gitlab.com/bucosys/dragiter/-/tags/2026.7.26](https://gitlab.com/bucosys/dragiter/-/tags/2026.7.26)

release: 2026.7.26 – production-stable with mTLS and hardened config pipeline
Promote dragiter from 2026.7.20rc2 (Beta) to Production/Stable.

### Added
- TLS / mTLS support: --ca-bundle-file, --client-cert-file, --client-key-file
  (custom CA, client cert, optional separate key via httpx SSLContext)
- Integer and Float settings from DRAGITER_* environment variables
- $VAR expansion for environment values before type conversion
- Unit tests for env int/float parsing, $ expansion, and precedence
- Unit tests for ApplicationManager (XDI), ContextWindowEstimator
- Functional tests for Ollama, Caddy CA-bundle and mTLS proxies
- Man-page entries for new TLS flags and cleaned ENVIRONMENT section

### Changed
- Version 2026.7.20rc2 → 2026.7.26
- Development Status: Beta → Production/Stable
- OpenAIService: explicit wait_time init, httpx client for TLS/mTLS
- Tests removed from the Wheel package (remain in the source distribution)
- Packaging and test layout refined for a stable release

### Fixed
- Env vars for max_context_tokens, max_output_tokens, temperature, etc.
  were silently ignored (only String/Bool/Path were handled)
- Fragile retry timing in OpenAIService (wait_time before first sleep)
- Duplicate / inconsistent DRAGITER_CONFIG documentation in info.txt
- Raised minimum Python version to 3.13 to match `Path.glob(recurse_symlinks=...)` usage in `resource_collector.py`; previously declared as `>=3.11`, which caused a crash on older interpreters.

## [2026.7.20rc2] - 2026-07-20
[https://gitlab.com/bucosys/dragiter/-/tags/2026.7.20rc2](https://gitlab.com/bucosys/dragiter/-/tags/2026.7.20rc2)

### Changed
- Removed `tests/outputs/` folder from package distribution (Wheel)
- Fixes installation error on Windows caused by excessively long paths
- Removed folder tests/outputs from package building

## [2026.7.20rc1] - 2026-07-20
[https://gitlab.com/bucosys/dragiter/-/tags/2026.7.20rc1](https://gitlab.com/bucosys/dragiter/-/tags/2026.7.20rc1)

### Changed
- Improved test stability by making the tiny functional test self-contained
- Removed broken test file `test_e2e_security_with_simulation.py`

## [2026.7.19rc1] - 2026-07-19
[https://gitlab.com/bucosys/dragiter/-/tags/2026.7.19rc1](https://gitlab.com/bucosys/dragiter/-/tags/2026.7.19rc1)

### Added
- Initial Release Candidate (RC1)
- Comprehensive user manual and examples
- Simulation mode for safe testing
- Filename sanitization and path traversal protection
- Activity logging (JSONL) for auditability
- JSONL loop support for batch processing
- Dual licensing (AGPL-3.0-or-later OR Proprietary)

### Changed
- Version bumped to RC1
- Improved documentation and getting started experience

### Security
- Strong filename sanitization and path containment checks
- Security tests included

### Known Limitations
- Token estimation is character-based (sufficient for most use cases)
- Test coverage is still growing (E2E + security tests present)

## [2026.07.06b1] - 2026-07-06

### Changed
- Promoted development status from **Alpha** to **Beta** in `pyproject.toml`
- Updated project documentation to reflect Beta maturity level

## [2026.07.03b1] - 2026-07-03
[https://gitlab.com/bucosys/dragiter](https://gitlab.com/bucosys/dragiter)

### Added
- Initial public alpha release of **dragiter** (Deterministic RAG Iterator)
- Full command-line interface with comprehensive option handling and configuration precedence (CLI → TOML → environment variables → defaults)
- Support for prompt templates in TOML format with `[system]`, `[task]`, `[behaviour]` and `[outcome]` sections
- Flexible material/resource loading via glob patterns and regex-based chunking (e.g. by Markdown headings or C function definitions)
- Loop processing for batch jobs using plain text files or JSON Lines (JSONL) with dynamic placeholder substitution
- Built-in context window estimation and validation using `chars_per_token`, `max_context_tokens` and `max_output_tokens`
- Simulation mode (`-s` / `--simulate`) for safe workflow testing without API calls
- Multiple output routing options: single file, directory with filename schema, append/overwrite/exclusive modes
- Detailed activity tracing to JSONL (`-a` / `--activity-file`)
- Native support for OpenAI-compatible LLM endpoints (Ollama, Grok/xAI, Google Gemini, LiteLLM proxies, etc.)
- Automatic retry logic with configurable delay and maximum attempts
- Self-contained documentation and example extraction commands (`dragiter-gen-docs`, `dragiter-gen-examples`)
- Comprehensive manual and multiple real-world example workflows
- Dual licensing: GNU AGPL-3.0-or-later (open source) or proprietary commercial licence

### Changed
- None (initial release)