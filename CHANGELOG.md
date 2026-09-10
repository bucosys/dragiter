# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
uses [Calendar Versioning](https://calver.org/)
in the form `YYYY.M.D` (with optional pre-release suffixes such as `rc1`, `b1`).

## [Unreleased]

### Changed
- Results (and the simulate run board) are echoed on stdout only when
  neither `output_file` (`-o`) nor `output_directory` (`-O`) is set.
  File routing replaces the default stdout sink; stdout redirection is
  not inspected.

## [2026.9.9] - 2026-09-09

[https://gitlab.com/bucosys/dragiter/-/tags/2026.9.9](https://gitlab.com/bucosys/dragiter/-/tags/2026.9.9)

### Added
- `--max-chunks` / `max_chunks` / `DRAGITER_MAX_CHUNKS`: raise or lower the
  tokenizer cap (default 200, minimum 1)
- `ContextValidationReport` now implements `ActivityProvider`: per-run
  summary and per-session token estimates (`estimated_input_tokens`,
  reserved output, calculated total, limit) are written to the activity
  file when `chars_per_token`, `max_context_tokens` and
  `max_output_tokens` are all set
- `--pack-limit-chars` / `pack_limit_chars` / `DRAGITER_PACK_LIMIT_CHARS`
  and per-section `pack_limit_chars` in the resource TOML: pack consecutive
  regex chunks of the same file up to N characters (`0` or unset = off).
  A globally set value, including `0`, overrides the section key
- Unit tests for chunk packing, resource-TOML `pack_limit_chars`, and
  validator range `merge_max_chars >= 0`
- Secure staging mechanism for directory outputs (`-O` option) to safeguard expensive LLM API results against unexpected file write conflicts.
- New infrastructure adapter `write_directory_with_staging` in `io_services` to handle 
  transactional file commits using hidden temporary directories (e.g. `.tmp_staging_<PID>`).

### Changed
- Keep `requires-python = ">=3.11"`. The 3.13-only `Path.glob(recurse_symlinks=...)`
  call was removed in 2026.8.16; the tree no longer needs a 3.13 floor.
- Pin the LLM stack to the current majors: `openai>=3.0.0,<4.0.0` and
  `httpx2>=2.7.0,<3.0.0`. The live adapter is coupled to
  `openai.DefaultHttpx2Client`.
- Simulate run board shows the effective pack budget and `pack from`
  (`cli` / `section` / `mixed` / `off`), `small / over`, and window
  facts. Session boards in `-o`/`-O` list session, file, chunk, section,
  valid, chars, tokens, pack, pack from and loop index. `sessions` is
  the request count (chunks × loop lines when sequential)
- `MaterialTokenizer` splits at regex match starts instead of pairing
  captured headers with bodies; capturing groups are no longer required
- Resource sections accept `regex_patterns` (list). Pattern 0 always
  runs; later patterns refine only pieces above `pack_limit_chars`.
  The singular key `regex_pattern` is no longer accepted; a section
  that still sets it aborts collection and names the section
- Context-window estimation logs the three parameters, per-session
  totals and a summary at `INFO` when verbose is on (previously
  `DEBUG`, which verbose never showed)
- Man page, manual and technical reference document `pack_limit_chars`
  (CLI, environment, resource schema, activity field)
- Refactored `OutputWriter` to delegate all low-level file system operations and staging 
  logic to the infrastructure layer, maintaining strict Clean Architecture boundaries.

### Fixed
- `PromptCreator` no longer reads stdin unconditionally. Stdin is consumed
  only when `-t` / `--task` is set or the prompt template contains `{STDIN}`
  in `task.first`. Non-interactive runs (`dragiter -s -p …`) no longer hang
  on an inherited, still-open stdin (CI, systemd, Docker without `-i`).
- Documentation now matches the breaking change: `regex_pattern` is rejected,
  not treated as an alias of `regex_patterns`.
- `PromptCreator` no longer reads stdin unconditionally. Stdin is consumed
  only when `-t` / `--task` is set or the prompt template contains `{STDIN}`
  in `task.first`. Non-interactive runs (`dragiter -s -p …`) no longer hang
  on an inherited, still-open stdin (CI, systemd, Docker without `-i`).
- Streaming completions requested `stream_options.include_usage` so
  `ChatResults.input_tokens` / `output_tokens` are filled from the
  provider instead of staying `0`
- Usage reader accepts both `prompt_tokens`/`completion_tokens` and
  `input_tokens`/`output_tokens`
- Context-window overflow is logged at `WARNING` instead of being
  dropped at `DEBUG`
- Prevented catastrophic data loss during application aborts caused by `IOServiceError` 
  (e.g. when a target file already exists whilst using exclusive mode `-m x`). 
  Failed final transfers now safely preserve all generated data within the 
  staging directory for easy recovery.

## [2026.9.1] - 2026-09-01

[https://gitlab.com/bucosys/dragiter/-/tags/2026.9.1](https://gitlab.com/bucosys/dragiter/-/tags/2026.9.1)

### Fixed
- Retry transient HTTP 500/502/503; `is_retryable()` previously returned
  False for every `APIStatusError` / `InternalServerError` except 429
- Do not label post-connect stream failures as OpenAI client
  initialisation / CA-bundle errors
- Document retry semantics (`max_retry` as attempt count, `retry_delay`
  default 3 s, SDK `max_retries=0`, logger heartbeat) in reference,
  manual, man page and README

### Changed
- `OpenAIServiceExt` retries only `APIConnectionError` and
  `APIStatusError`; other exceptions fail the attempt immediately
- Remove unused `_print_watch()` stdout spinner

### Added
- Unit tests for `CompletionRetryPolicy` and the streaming retry loop
- SPDX license identifiers (`SPDX-License-Identifier`, `SPDX-FileCopyrightText`) added 
  to all source files, replacing the absence of per-file licensing metadata and enabling 
  automated REUSE compliance checks.


## [2026.8.31] - 2026-08-31

[https://gitlab.com/bucosys/dragiter/-/tags/2026.8.31](https://gitlab.com/bucosys/dragiter/-/tags/2026.8.31)

### Added
- `--tcp-keep-alive` / `TCPKeepAliveBoolSetting` (CLI, config, `DRAGITER_TCP_KEEP_ALIVE`) and man-page / reference coverage
- `tcp_keep_alive = true` in the Ollama example config
- `OpenAIServiceExt`: always-on streaming via the OpenAI SDK (`httpx2` / `DefaultHttpx2Client`), unlimited read timeout for long-running local models, optional TCP keepalive socket options
- Verbose streaming heartbeat (`logger.info`) while a completion is still running
- Resolve a relative `--config-file` / `-c` path against `--base-directory` / `-b` before loading

### Changed
- CLI now wires `OpenAIServiceExt` instead of the non-streaming `OpenAIService`
- Split application logging: worker start / progress at `INFO`, payload dumps at `DEBUG`
- `BaseDirectoryPathSetting` is no longer pre-filled with the process CWD; it is set only when `-b`, the config file or `DRAGITER_BASE_DIRECTORY` supplies a value. Resource globs without an explicit section `base_directory` still start from CWD and are then rebased when `-b` is set *and* the original path was relative
- Tests aligned to the current settings / parameter-object / `ApplicationManager.provide(worker, data)` API
- Simulate-mode and CLI infrastructure tests run the worker chain in-process so they no longer require a live `openai` / `httpx2` install or a subprocess import of the streaming adapter
- Shared test helpers in `tests/support.py`
- Extract retry policy and HTTP transport factory into 
- Disable OpenAI SDK retries (max_retries=0); the adapter owns the loop

### Fixed
- Config-file discovery when `-c` is relative and `-b` relocates the workspace root
- Resource-collector tests now set section `base_directory` explicitly, matching the “no implicit CWD preset” behaviour
- Do not retry HTTP 504, stream-timeout or an Ollama runner crash


## [2026.8.20] - 2026-08-20

[https://gitlab.com/bucosys/dragiter/-/tags/2026.8.20](https://gitlab.com/bucosys/dragiter/-/tags/2026.8.20)

### Fixed
- Honour `Chunk.valid` flag set by `include_filters` / `exclude_filters`
  when assembling prompts (sequential mode skips invalid chunks,
  batched mode injects only valid ones). Also report the selection
  in the activity log (`Material.to_activity_dict_list`).
- Include `openai.APITimeoutError` in the retryable exceptions of
  `OpenAIService` so transient proxy/LLM timeouts are retried.

### Changed
- Unify boolean parsing for TOML strings and environment variables:
  accept the truthy set `TRUE` / `1` / `YES` (case-insensitive)
  instead of only `"true"`. Aligns ConfigurationLoader with
  LoggingConfigurator.
- Expand Python classifiers to 3.11-3.13 and add `ruff>=0.16.3`
  plus a full `[tool.ruff]` configuration to `pyproject.toml`.
- Point Documentation URL to https://www.dragiter.app/.
- Apply ruff lint and format across the codebase for consistent style.

## [2026.8.16] - 2026-08-16

[https://gitlab.com/bucosys/dragiter/-/tags/2026.8.16](https://gitlab.com/bucosys/dragiter/-/tags/2026.8.16)

### Added

- MkDocs-based project documentation under `web/` (including index.md with logo and links)
- GitLab CI pipeline: unit tests on Python 3.13 + automatic documentation deployment via GitLab Pages
- Legal Notice (Impressum) and Privacy Policy (English, DDG/MStV compliant)
- Set `site_url` to https://www.dragiter.app/
- Circuit breakers: 100 MB file size limit in `SimpleTextFileReader`
- Circuit breakers: 200 chunk limit and size warnings (<50 / >20k chars) in `MaterialTokenizer`
- Circuit breakers: 50 item limit in `LoopBuilder` to prevent combinatorial explosion and API cost spikes
- Documented the existing circuit-breaker limits and soft chunk-size warnings in the Technical Reference and Manual
- Expanded `tests/README.md` with live cloud E2E key setup and Caddy TLS/mTLS recipes

### Changed

- Complete rewrite of documentation following the Diátaxis framework (new Tutorial / How-to / Explanation Manual +
  separate Technical Reference)
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
- Memory leak: `FileActivityLogger` now clears the buffer after syncing or when disabled
- OOM vulnerability: `write_or_append_lines_to_unique_file` uses a direct append stream (`mode="at"`) instead of loading
  files into RAM
- Enabled local hosting of Google Fonts via the MkDocs privacy plugin to ensure strict GDPR compliance.
- Updated legal notice (Impressum) for German DDG compliance and changed contact phone number.

## [2026.7.26] - 2026-07-26

[https://gitlab.com/bucosys/dragiter/-/tags/2026.7.26](https://gitlab.com/bucosys/dragiter/-/tags/2026.7.26)

release: 2026.7.26 - production-stable with mTLS and hardened config pipeline Promote dragiter from 2026.7.20rc2 (Beta)
to Production/Stable.

### Added

- TLS / mTLS support: --ca-bundle-file, --client-cert-file, --client-key-file (custom CA, client cert, optional separate
  key via httpx SSLContext)
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

- Env vars for max_context_tokens, max_output_tokens, temperature, etc. were silently ignored (only String/Bool/Path
  were handled)
- Fragile retry timing in OpenAIService (wait_time before first sleep)
- Duplicate / inconsistent DRAGITER_CONFIG documentation in info.txt
- Raised minimum Python version to 3.13 to match `Path.glob(recurse_symlinks=...)` usage in `resource_collector.py`;
  previously declared as `>=3.11`, which caused a crash on older interpreters.

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
- Full command-line interface with comprehensive option handling and configuration precedence (CLI → TOML → environment
  variables → defaults)
- Support for prompt templates in TOML format with `[system]`, `[task]`, `[behaviour]` and `[outcome]` sections
- Flexible material/resource loading via glob patterns and regex-based chunking (e.g. by Markdown headings or C function
  definitions)
- Loop processing for batch jobs using plain text files or JSON Lines (JSONL) with dynamic placeholder substitution
- Built-in context window estimation and validation using `chars_per_token`, `max_context_tokens` and
  `max_output_tokens`
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