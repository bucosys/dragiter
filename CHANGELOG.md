# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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