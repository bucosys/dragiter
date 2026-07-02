# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2026.7.3b1] - 2026-07-03

### Added
- Initial public alpha release of **dragiter** (Deterministic RAG Iterator)
- Full command-line interface with comprehensive option handling and configuration precedence (CLI → TOML → environment variables → defaults)
- Support for prompt templates in TOML format with `[system]`, `[task]`, `[behaviour]` and `[outcome]` sections
- Flexible material/resource loading via glob patterns and regex-based chunking (e.g. by Markdown headings or C function definitions)
- Loop processing for batch jobs using plain text files or JSON Lines (JSONL) with dynamic placeholder substitution (`{LOOP_CONTENT}`, JSON keys, etc.)
- Built-in context window estimation and validation using `chars_per_token`, `max_context_tokens` and `max_output_tokens`
- Simulation mode (`-s` / `--simulate`) for safe workflow testing without API calls
- Multiple output routing options: single file, directory with filename schema, append/overwrite/exclusive modes
- Detailed activity tracing to JSONL (`-a` / `--activity-file`)
- Native support for OpenAI-compatible LLM endpoints (Ollama, Grok/xAI, Google Gemini, LiteLLM proxies, etc.)
- Automatic retry logic with configurable delay and maximum attempts
- Verbose and debug logging with optional log file output
- Self-contained documentation and example extraction commands (`dragiter-gen-docs`, `dragiter-gen-examples`)
- Comprehensive manual and multiple real-world example workflows (Markdown analysis, C code security audit, marketing copy generation)
- Dual licensing: GNU AGPL-3.0-or-later (open source) or proprietary commercial licence

### Changed
- None (initial release)

### Deprecated
- None (initial release)

### Removed
- None (initial release)

### Fixed
- None (initial release)

### Security
- None (initial release)

---

**Notes for this release**
- This is an **alpha** release (Development Status: 3 - Alpha). The tool is already highly usable for personal and team automation, but the public API and internal architecture may still evolve.
- The project was developed with significant assistance from Grok and Gemini as pair-programming partners.
- All code, variable names, function names and configuration keys are in clear international English. Documentation and comments follow British English spelling and tone.
- Recommended next steps: run the included examples with `-s` (simulate) first, then configure your preferred LLM backend via `config-ollama.toml`, `config-grok.toml` or environment variables.

[2026.7.3b1]: https://gitlab.com/bucosys/dragiter/-/tags/2026.7.3b1