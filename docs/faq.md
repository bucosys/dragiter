# dragiter FAQ

**Version:** derived from source (2026.9.29)  
**Language:** British English  
**Audience:** power users and the maintainer  
**Scope:** Recurring support questions. Not a second manual and not a second reference.  
**Sources:** `docs/manual.md`, `docs/reference.md`, `docs/info.txt`, `CHANGELOG.md`, `README.md`, example READMEs, and the 2026.9.29 tree

This document answers questions that keep coming back. Complete procedures live in the [Manual](manual.md). Exact flags, schemas, ranges and activity-log records live in the [Technical Reference](reference.md). When those two disagree with this page, name the file and the version and treat this page as uncertain.

British English is used throughout.

---

## How to extend this page

Add content at the **end of an existing section**, or add a **new numbered section after the last one**. Do not renumber headings that already exist. MkDocs permalinks are derived from the heading text; renaming a question breaks deep links.

Each question is a self-contained `###` block in this order:

1. Short answer
2. Command or TOML fragment
3. Typical pitfall
4. Pointer to Manual versus Reference
5. What the reporter should send (`-v` board, activity JSONL, `.tmp_staging_file_*` / `.tmp_staging_dir_*`)

Keep one concern per question. If a topic grows past a screen, split it into a new `###` with a new title instead of editing the old title. Do not introduce admonition syntax, tabbed fences or other Material extras — `mkdocs.yml` currently enables only `search` and `privacy`.

This file is already published on the site next to `manual.md` / `reference.md`: `.gitlab-ci.yml` copies `docs/*.md` into `web/`, and `mkdocs.yml` already carries its nav entry:

```yaml
nav:
  - Home: index.md
  - Manual: manual.md
  - Reference: reference.md
  - FAQ: faq.md
```

---

## 1. Product identity

### What is dragiter?

A focused command-line tool that turns a deterministic combination of material, a prompt template and optional loop data into one or more OpenAI-compatible chat-completion requests, then routes the answers by explicit rules. There is no chat UI and no hidden session state. Live completions always stream.

```bash
pip install dragiter   # Python >= 3.11
dragiter --version
dragiter --info
```

Typical pitfall: looking for a web console or a conversation store. Provider choice is only `base_url`, `model_name` and `api_key`.

See Manual, Design philosophy. See Reference §1a and §8.

If it is unclear, send `dragiter --version` and the exact command line.

### What must not be claimed about the product?

It is a CLI. Configuration precedence is CLI, then TOML (`-c` / `DRAGITER_CONFIG_FILE` / `~/.config/dragiter/config.toml`), then `DRAGITER_*` environment variables, then defaults. From 2026.9.9 the singular resource key `regex_pattern` is rejected. Standard input is read only with `-t` / `--task` or the placeholder `{STDIN}`. Results appear on stdout only when neither `-o` nor `-O` is set. `-v` writes the run board to stderr. `-s` simulates with no network and no tokens.

Typical pitfall: documenting flags or breaking changes that are not in the 2026.9.29 sources.

See README Compatibility and Reference §1.

If it is unclear, send the flag the user believes exists, plus `dragiter --help` and `dragiter --info`.

---

## 2. Install, versions and shipped extras

### How do I install it, and which Python does it need?

Install from PyPI. `requires-python` is `>= 3.11` (3.11–3.13 are classified). The live adapter needs `openai>=3.0.0,<4.0.0` and `httpx2>=2.7.0,<3.0.0`. openai 1.x / 2.x do not export `DefaultHttpx2Client`.

```bash
pip install dragiter
python3 --version
```

Typical pitfall: an environment that already pinned openai 1.x will import, then fail when the CLI constructs the streaming client. Tests are not inside the wheel; they live in the sdist.

See README Installation, Reference §1a, and `pyproject.toml` of 2026.9.29.

If it is unclear, send `pip show dragiter openai httpx2` and `python3 --version`.

### How do I get the examples and the Diátaxis docs after pip install?

The wheel embeds `docs/` and `examples/`. The helper entry points extract them.

```bash
dragiter-gen-examples .
cd examples/01_md_sample
dragiter-gen-docs .
```

Typical pitfall: working from the wrong directory means resource globs match nothing. Example 04 is explicit: if the profile file is not in the current working directory or in `-b`, you get `session_0001.md`, `file none`, and raw `{CHUNK_*}` placeholders.

See Manual Tutorial steps 1–2 and `examples/04_staged_regex_sample/04_README.md`.

If it is unclear, send `ls` of the working directory and the `-p` / `-r` / `-b` values.

### How do I run the test suite?

The suite is not in the installed wheel. Download the sdist, install the development extra, run pytest. Most tests need no network. Optional Ollama and cloud end-to-end tests skip when the service or keys are missing.

```bash
pip download dragiter --no-binary=:all: -d .
tar xf dragiter-*.tar.gz
cd dragiter-*/
pip install -e ".[dev]"
pytest -q
```

Typical pitfall: functional Ollama / Caddy tests look broken when they are only skipped.

See Manual, Running the test suite, and `tests/README.md`.

If it is unclear, send `pytest -q` output and whether Ollama is listening on port 11434.

---

## 3. First run and simulation

### What is the first command that should always be run?

Simulate. `-s` makes no API call and spends no tokens. With neither `-o` nor `-O`, stdout now prints full detail: the aggregate run board (sessions as request count, mode, chunks, loops, pack budget and origin, small/over, window), followed by every session's own board and its complete outgoing request (role/content payload table) — the same content `-o` writes to a file. `ChatManager` builds this content and persists it as an ordinary shard for every session (plus one leading aggregate-board shard for `-o`/stdout-only); `OutputWriter` then commits it the same way for stdout, `-o` and live runs alike.

```bash
dragiter -s -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt
```

Typical pitfall: expecting stdout-only to show *just* the aggregate board, as it used to. It does not any more — treat a stdout-only simulate run as a full transcript dump, and use `-O` when a directory of separate files is wanted instead. Shell redirection of stdout is not treated as a file sink.

See Manual Tutorial §2, Reference §9 (Simulate boards), `design/specs/spec-simu-simulation.md` §4.3, and README Quick Start.

If it is unclear, send the simulate board text and whether `-o` or `-O` was set.

### The terminal looks frozen on a local model. Is it dead?

Usually not. Live calls stream with an unlimited read timeout. Use `-v`. Verbose writes a labelled board on stderr: a start block (prefix `▷`: model, mode, sessions, chunks/files, pack, window, peak, output), one request line per call with a pulse mark `◷◶◵◴` advancing at most every ten seconds from the stream loop, then a closing block (prefix `□`). With `-o` or `-O`, completions also land in the typed staging workspace beside the target. Pair long local runs with `--tcp-keep-alive`.

```bash
dragiter -v --tcp-keep-alive -c config-ollama.toml \
  -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt
```

Typical pitfall: `-v` never writes onto the result sink. With `-d` the board is mixed into the debug stream. The closing-block glyph is `□` (`END_MARK`, U+25A1 WHITE SQUARE, `stderr_session_board.py`) — an older CHANGELOG entry printed it as `■`, but the shipped code and `docs/reference.md` agree on `□`.

See Manual Tutorial §3, Reference §1a, and CHANGELOG 2026.9.13.

If it is unclear, send the `-v` stderr, a listing of `.tmp_staging_file_*` / `.tmp_staging_dir_*`, and whether `finish_reason` arrived. 2026.9.13 returns on `finish_reason` instead of waiting for a trailing usage event that some local runtimes never send.

---

## 4. Configuration precedence

### In which order are settings resolved?

Highest first: command-line arguments; TOML configuration file; environment variables `DRAGITER_*`; built-in defaults. A higher source never yields to a lower one. Therefore `DRAGITER_API_KEY` cannot override `api_key` already present in the loaded TOML.

```bash
export DRAGITER_API_KEY="xai-…"
dragiter -v -c config-grok.toml -p prompt.toml -r resource.toml
# leave api_key commented out inside every config-*.toml
```

Typical pitfall: putting a real key in TOML and then “overriding” it from the environment. A relative `-c` is rebased onto `-b` before the file is read; an absolute `-c` is left alone. `config_file` is not part of the later general path-rebase pass. `base_directory` is not pre-filled with the current working directory.

See Manual, Configuration precedence, and Reference §1.

If it is unclear, send the `-c` file with secrets masked, `env | grep DRAGITER`, and the full argument vector.

### Why did temperature, sequential processing or the output schema not come from my prompt file?

Those four keys have a special stack once `-p` is supplied: CLI, then the main configuration system (TOML or environment), then the prompt `[behaviour]` / `[outcome]` sections, then PromptCreator hard-coded defaults (`temperature = 0.0`, `sequential_processing = false`, `output_delimiter` a newline, `output_filename_schema = "dragiter-out.txt"`).

```toml
[behaviour]
temperature = 0.0
sequential_processing = false

[outcome]
output_delimiter = "\n---\n"
output_filename_schema = "sample_01.txt"
```

Typical pitfall: a prompt that omits `[behaviour]` still runs. The missing section is then blamed for values that were set on the CLI or in the main config.

See Reference §1 (special case) and §5 / §11 (PromptCreator defaults).

If it is unclear, send the prompt TOML, the config TOML, and whether `--temperature` or `--sequential-processing` was on the CLI.

### How are booleans parsed?

Environment values go through `BoolSetting.from_string` after strip and case-fold. Truthy: `TRUE`, `1`, `YES`, `ON`, `Y`. Falsy: `FALSE`, `0`, `NO`, `OFF`, `N`. Anything else, including empty, raises. Early logging (before the loader) only treats `TRUE`, `1` and `YES` as truthy for debug/verbose and derives names from `sys.argv[0]`, so `DRAGITER_DEBUG` is reliable when the process name is exactly `dragiter`. Prefer `-d` / `-v` / `-L` if the executable path is absolute. In the TOML config file use native booleans (`simulate = true`). Quoted boolean strings there are rejected.

```toml
simulate = true
# not simulate = "true"
```

Typical pitfall: copying a shell `TRUE` into TOML as a quoted string.

See Reference §3 and `docs/info.txt` ENVIRONMENT.

If it is unclear, send the exact TOML line and the environment value, quoted.

---

## 5. Resources, chunking and packing

### Why does my resource file die on regex_pattern?

2026.9.9 is a breaking release. The singular key is no longer accepted. Collection aborts and names the section. Use `regex_patterns` as a list. Pattern 0 always cuts at match starts; the match text stays on the following piece; capturing groups are ignored. Later patterns run only on pieces that still exceed `pack_limit_chars`. If the list is omitted the default is a pattern that matches nothing.

```toml
[config01]
glob_patterns = ["docs/**/*.md"]
regex_patterns = ['^#+\s+.*$', '\n\n']
```

Typical pitfall: old files and blog snippets still show `regex_pattern`. That is not an alias.

See README Compatibility, Manual “How to define material”, Reference §6, and CHANGELOG 2026.9.9.

If it is unclear, send the resource TOML and the exact abort line that names the section.

### How does pack_limit_chars actually work?

After the staged split and any `chunk_substitutions`, consecutive chunks from the same file are joined until the character budget would be exceeded. Unset or `0` disables packing and also disables overflow patterns after the first. A globally set value — including `0` — overrides the section key (CLI `--pack-limit-chars`, config `pack_limit_chars`, `DRAGITER_PACK_LIMIT_CHARS`). Packing never crosses a file or section boundary. Valid and invalid chunks are not mixed. A piece that no remaining pattern can reduce stays intact. `pack from` on the board is `cli`, `section`, `mixed` or `off`.

```bash
dragiter -s --pack-limit-chars 0 -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml
dragiter -s -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml
```

Typical pitfall: expecting later regular expressions to run when pack is off. Example 04 uses a section budget of 500 so long `##` chapters still hit `###`.

See Reference §6, Manual material how-to, `examples/04_staged_regex_sample/04_README.md`, and CHANGELOG 2026.9.13.

If it is unclear, send the simulate board (`pack`, `pack from`, `small/over`) and the resource section.

### What are chunk_substitutions?

Optional per-section ordered list of `{ pattern, replacement }` tables, added in 2026.9.13. After the staged split each piece is rewritten with `re.sub` in list order. The replacement is **literal**: `\1` and `\g<name>` are ordinary characters, not group references. Flags are `re.MULTILINE` only (not `IGNORECASE`). An empty replacement deletes the match. A piece that is empty or only whitespace afterwards is discarded. Include/exclude filters and `pack_limit_chars` then see the rewritten text. The first split still runs on the raw file. There is no CLI or environment override. Missing fields abort collection and name the section; an invalid pattern fails tokenisation with section and index.

```toml
chunk_substitutions = [
  { pattern = '[ \t]{2,}', replacement = " " },
  { pattern = '\n{3,}', replacement = "\n\n" },
]
```

Typical pitfall: writing backreferences in `replacement` and expecting group expansion.

See Reference §6 and CHANGELOG 2026.9.13 Added.

If it is unclear, send the substitutions block and the tokenisation error (section and index).

### Why were some files skipped?

Resolved matches that escape the section root, including symbolic links that point outside, are skipped. Globs are relative to the section search root: section `base_directory` if set, otherwise `Path.cwd()`. When `-b` is set, that root is rebased onto `-b` only if the original value was relative. An absolute section `base_directory` is not moved by `-b`.

```bash
dragiter -b examples/04_staged_regex_sample \
  -p examples/04_staged_regex_sample/04_prompt_staged_regex.toml \
  -r examples/04_staged_regex_sample/04_resource_staged_regex.toml \
  -s -O out
```

Typical pitfall: running from a parent directory without `-b` and wondering why zero files loaded.

See Reference §6 and Manual “How to define material”.

If it is unclear, send the current working directory, `-b`, each section `base_directory`, and the `Resources` record from `-a`.

### How do include_filters and exclude_filters interact with sequential mode?

`Chunk.valid` is honoured when prompts are assembled. Sequential mode skips invalid chunks; batched mode injects only valid ones. Valid and invalid chunks are never packed together.

Typical pitfall: a filter that marks almost everything invalid still “runs” and produces odd session boards (`file none`, leftover placeholders) rather than a hard abort.

See CHANGELOG 2026.8.20, Reference §6, and the session-board `valid` column in Reference §9.

If it is unclear, send the activity `Material` records and a session-board line with `valid yes/no`.

---

## 6. Prompts, standard input and loops

### What belongs in a prompt file?

TOML with `[system]` instruction, `[task]` `first` / `material` / `synthesis`, optional `[behaviour]` and `[outcome]`. Placeholders recognised in templates: `{CHUNK_NUM_ID}` (also `{CHUNK_NUM_ID:04d}`), `{CHUNK_FILE_NAME}`, `{CHUNK_SECTION_NAME}`, `{CHUNK_SECTION_NUM_ID}`, `{CHUNK_CONTENT}`, `{LOOP_CONTENT}`, `{LOOP_NUM_ID}` and any other keys from a JSONL loop object, plus `{STDIN}`.

```toml
[task]
first = """### REFERENCE MATERIAL"""
material = """FILE: {CHUNK_FILE_NAME}\n{CHUNK_CONTENT}"""
synthesis = """{LOOP_CONTENT}"""
```

Typical pitfall: outside simulation, `base_url` plus either `-p` or `-t` is required. A loop normally also wants a resource file.

See Manual “How to write a prompt template” and Reference §5.

If it is unclear, send the prompt TOML and whether `-t` was combined with `-p`.

### When is standard input read? Why did CI hang before 2026.9.9?

Standard input is consumed only when `-t` / `--task` is set (stdin then becomes the `first` field) or when `{STDIN}` appears in `task.first`. Templates without the placeholder do not touch stdin. That used to hang in CI, systemd and Docker without `-i` when `PromptCreator` read stdin unconditionally.

```bash
curl -s https://example.com/pricing \
  | dragiter -p summarize_pricing.toml -r web_resources.toml -o pricing_report.txt
```

Typical pitfall: piping into a prompt that has no `{STDIN}` and no `-t`. The pipe is ignored. Also: `-o` replaces the stdout sink, so a pipeline that both pipes in and expects the answer on stdout will look empty.

See Reference §5 `{STDIN}`, CHANGELOG 2026.9.9, and README Tool Chaining.

If it is unclear, send the prompt `task.first` block and whether the process inherited an open stdin.

### How do loop files work, and what is the 50-item cap?

Plain text: each non-empty line becomes `{LOOP_CONTENT}`. JSONL: one JSON object per line; every key is a placeholder. The entire prompt runs once per line. `LoopBuilder` aborts above 50 items. Sequential mode multiplies valid chunks by loop lines for the session count; without a loop file the multiplier is one.

```json
{
  "language": "German",
  "region": "DACH",
  "tone": "formal"
}
```

Typical pitfall: a 51st marketing variant is not “a bit extra”; it is a hard `LoopBuilderError`. Split the file.

See Manual “How to iterate”, Reference §7 and Reference §2 (hard limits).

If it is unclear, send `wc -l` of the loop file and the `Loop` activity record.

---

## 7. Output routing and the stdout contract

### Where do results go?

Stdout is the default result sink. Once `output_file` (`-o`) or `output_directory` (`-O`) is set from any configuration source, file routing replaces that sink. Live replies and the simulate run board are written only to the requested file(s). Redirection of stdout is not inspected; `isatty()` cannot distinguish a user pipe from CI capture.

```bash
dragiter -s -p prompt.toml -r resource.toml            # board + every session's request on stdout
dragiter -s -p prompt.toml -r resource.toml -O out     # files; stdout quiet
dragiter -p prompt.toml -r resource.toml -o all.md -m a
```

Typical pitfall: using `-o` and also expecting a stream on stdout. To keep a stream, omit `-o`/`-O` and redirect, or read the written file.

See Reference §9, CHANGELOG 2026.9.13 Changed, and README stdout contract.

If it is unclear, send whether `-o` / `-O` / `DRAGITER_OUTPUT_*` was set, plus the first lines of stdout versus the file.

### What do -m x|w|a and -O staging do?

`output_mode` default is `x` (exclusive create; fails if the file exists), `w` overwrite, `a` append. `output_delimiter` is inserted between multiple results in the same file and between existing bytes and a new `-m a` block. `-o` stages in a plain directory named exactly `.tmp_staging_file_<PID>` (no suffix) beside the file. `-O` stages in `.tmp_staging_dir_<PID>/` inside the target. `-m` is applied only at commit. `-m x` is rejected before the first completion when names are known. On a later write conflict the process aborts and leaves the workspace.

```bash
dragiter -p audit_prompt.toml -r legacy_code_resource.toml -O ./audit_results -m x
```

Typical pitfall: re-running a batch with `-m x` and assuming a clean overwrite. Look in `.tmp_staging_file_*` / `.tmp_staging_dir_*` before declaring data loss. Filenames from `output_filename_schema` accept `CHUNK_*` and loop keys and are sanitised. `TIMESTAMP` defers the early `-m x` check.

See Manual “How to control where results are written” and Reference §9.

If it is unclear, send the target directory listing including hidden staging folders, and `output_mode`.

### What replaced .dragiter-partial/?

`.dragiter-partial/` is gone. Mid-run drafts live in `.tmp_staging_file_<PID>/` next to `-o`, or in `.tmp_staging_dir_<PID>/` inside `-O`. Stdout-only also stages, in `.tmp_staging_stdout_<PID>/` under the user's default temp directory (`$TMPDIR` if set and usable, otherwise the platform default) — never the current working directory. So even with neither `-o` nor `-O`, something is stored between completions; only the location differs.

```bash
ls -la .tmp_staging_file_* .tmp_staging_dir_*
ls -la "${TMPDIR:-/tmp}"/.tmp_staging_stdout_*
```

Typical pitfall: treating the workspace as the final routed output. Final commit still goes through `-o` / `-O` / stdout after the last completion.

See Reference §1a and CHANGELOG 2026.9.26.

If it is unclear, send the workspace listing and the failing attempt message (`Attempt n/m`).

### How do I resume an aborted -O run?

Add `--resume`. It requires `-O`; with `-o` or stdout-only, the run is rejected before anything starts. Right after the new run's own workspace is created, dragiter looks for other `.tmp_staging_dir_*` directories directly inside the same `-O` directory (none is not an error), picks the most recently modified one, moves its shards into the new workspace (a same-filesystem rename, not a copy), and removes the emptied source directory. A session whose shard is already there is never sent to the LLM — live or simulate — and is reported as `reused` on the board instead of generating a new reply; the final commit does not distinguish an adopted shard from a freshly persisted one.

```bash
dragiter -p prompt.toml -r resource.toml -l loop.jsonl -O out -m w --resume
```

Typical pitfall: expecting `--resume` to notice that the material, loop file, prompt or `--sequential-processing` changed since the aborted run. It does not — there is no manifest or fingerprint, only shard position — so a changed run resumed this way silently attributes an old reply to the wrong session. Re-run without `--resume` after changing inputs.

See Reference §9 “Resume” and CHANGELOG 2026.9.29.

If it is unclear, send the adoption line from stderr (printed regardless of `-v`, naming the source workspace and shard count), the `-v` board if it was used, and the staging directory listing before and after the resumed run.

---

## 8. Context window, tokens and circuit breakers

### Why does the board say window n/a and peak -- / --?

Window facts stay `n/a` / `--` until `chars_per_token`, `max_context_tokens` and `max_output_tokens` are all set. From 2026.9.13 the estimator records `is_valid`, `max_session_tokens` and `max_tokens_limit` as `None` when the trio is incomplete — not `yes` and `0 / 0`. Token estimation is characters divided by `chars_per_token`. The session-board `tokens` column is not `chars / chars_per_token`; it is estimated input of every message in the session plus reserved `max_output_tokens`. That same total feeds `peak / limit`. Estimated input alone is written to the activity file as `estimated_input_tokens`. Requests over the remaining budget (`max_context_tokens` − `max_output_tokens`) are refused before the network call.

```toml
chars_per_token = 3.8
max_context_tokens = 32000
max_output_tokens = 4000
```

Typical pitfall: setting only two of the three values and believing the window is enforced. Conventional `3.8` is documented in the shipped `examples/*/config-*.toml` files and in `docs/window-starting-values.md`; it is not a validator default.

See Manual “How to keep requests inside the window”, Reference §2 / §9 / §11, and CHANGELOG 2026.9.13 Fixed.

If it is unclear, send the three settings with their origin (CLI / TOML / environment) and the run-board window/peak lines.

### What are the hard limits?

100 MB per input file (`SimpleTextFileReader`). Maximum chunks 200, or `max_chunks` if set (minimum 1) in `MaterialTokenizer`. Maximum 50 loop items in `LoopBuilder`. A soft warning (run continues) fires for a final chunk shorter than 50 characters (`small` on the run board); a final chunk longer than the effective pack budget is counted as `over` — there is no fixed character threshold such as 20,000 for this, since `over` is measured against `pack_limit_chars`, not a constant. When pack is `off` or `mixed`, `over` is always 0. A run that would exceed the chunk cap aborts unless `--max-chunks` / `max_chunks` / `DRAGITER_MAX_CHUNKS` raises it.

```bash
dragiter -s --max-chunks 1 -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml
```

Typical pitfall: raising `max_chunks` to “fix” a bad regular expression instead of tightening the split. The cap exists to stop combinatorial explosion.

See Manual, Hard safety limits, and Reference §2 Hard limits.

If it is unclear, send the abort message (file size versus `max_chunks` versus `LoopBuilderError`) and any chunk-size warnings from `-v` / `-d`.

---

## 9. Providers, streaming, retries and TLS

### How do I point dragiter at Ollama, xAI or Google?

Any OpenAI-compatible chat-completions endpoint. Change three values. Example configs ship under `examples/01_md_sample/`. Do not put a live key in those files.

```bash
dragiter ... --base-url "http://localhost:11434/v1" \
             --model-name "llama3" \
             --api-key "dummy-key"

# xAI
dragiter ... --base-url "https://api.x.ai/v1" \
             --model-name "grok-4.3" \
             --api-key "YOUR_XAI_KEY"
```

Typical pitfall: Ollama still wants some `api_key` string. `base_url` is optional only in simulation. Mandatory live settings: `base_url`, and either `-p` or `-t`.

See Manual “How to connect” / “How to supply API keys” and Reference §2 Mandatory settings.

If it is unclear, send `base_url`, `model_name` (not the key), and a masked `AIServiceParameters` activity record.

### What is retried, and what is max_retry?

The OpenAI SDK retries are disabled (`max_retries=0`). `CompletionRetryPolicy` owns the loop. `max_retry` is the number of completion **attempts**, not extra tries. Unset or `0` means one try (validator range 0–9; the adapter still does `max(1, value)`). `retry_delay` when unset is 3 s at runtime (validator 0–20). Backoff before attempt *n* (1-based): no wait on attempt 1; then delay, 2×, 4×.

Retried: HTTP 429, transport/connection failures, transient 5xx that is not a gateway timeout (500/502/503).

Not retried: HTTP 504, messages containing `gateway timeout` or `stream timeout`, `APITimeoutError`, an Ollama runner crash (`model runner has unexpectedly stopped`), client 4xx other than 429.

Transport or SDK construction failures say `Failed to initialise OpenAI client …`. Failures after the client exists say `Attempt n/m failed: …`. They are not labelled as certificate or CA-bundle problems.

```toml
max_retry = 3
retry_delay = 5
```

Typical pitfall: repeating a 504 or a crashed Ollama runner with a higher `max_retry`. That will not recover a heavy prompt. CHANGELOG 2026.8.20 said the legacy non-streaming `OpenAIService` retried `APITimeoutError`; the CLI no longer wires that adapter.

See Reference §1a Retries, Manual Explanation (retries), and CHANGELOG 2026.9.1 / 2026.8.31.

If it is unclear, send the exact error string (init versus `Attempt n/m`), `max_retry`, and the provider status code.

### How do TLS, mTLS and custom CAs work?

Optional flags: `--ca-bundle-file`, `--client-cert-file`, `--client-key-file`. `client_key_file` without `client_cert_file` is rejected. Functional tests exist for Caddy CA-bundle and mTLS.

```bash
dragiter --ca-bundle-file /path/ca.pem \
         --client-cert-file /path/client.pem \
         --client-key-file /path/client-key.pem ...
```

Typical pitfall: a stream drop after connect is not a CA-bundle error. Do not retell it as TLS unless the failure is on client initialisation.

See Reference §2 validation, CHANGELOG 2026.7.26 Added, and `tests/README.md`.

If it is unclear, send whether the error is `Failed to initialise OpenAI client` plus the three path settings (not the key material).

---

## 10. Activity log, verbose and debug

### What should a user send when a run misbehaves?

Ask for a short, reproducible packet rather than a narrative. Prefer: full argument vector; `dragiter --version`; simulate board (no `-o`/`-O`); `-v` stderr; activity JSONL from `-a`; listing of `.tmp_staging_file_*` / `.tmp_staging_dir_*`; resource and prompt TOML with secrets removed.

Activity is JSON Lines, UTF-8, appended, never truncated by the logger. Envelope fields `TS` (UTC) and `RT` (producer class). Keys containing the substring `key` (case-sensitive) become `***MASKED***` — so `api_key` is masked, other fields are clear text.

```bash
dragiter -s -v -a activity.jsonl -p prompt.toml -r resource.toml -l loop.txt
# then the live twin with -v -a activity-live.jsonl
```

Typical pitfall: sending only “it hung” with no board and no record of whether `-o` was set. Payload dumps stay on DEBUG (`-d`); `httpx2` request lines stay off without `-d`.

See Reference §10 and Manual, Activity logging.

Typical `RT` order: start → settings → `Resources` → `Material` → `Loop` → `PromptTemplate` → `ChatSessions` → `ChatResults` → `ApplicationResult` `SUCCESS` or `FAILURE`.

---

## 11. Source discrepancies

When shipped files disagree, name both and stay uncertain. Do not silently pick a winner.

| Topic | What the files say |
|---|---|
| `APITimeoutError` retry | CLI path (`OpenAIServiceExt`, 2026.8.31+): not retried. A 2026.8.20 CHANGELOG note says the legacy non-streaming `OpenAIService` used to retry it; that module has since been deleted from the tree entirely (it was already unwired before removal), so the note is history only. |
| Activity start banner version | Reference §10 sample still shows `dragiter(2026.7.26)` in the illustrative JSON. Treat as an example record, not the running version. |

---

## 12. Maintainer map

Use this table when the FAQ answer is not enough and the tree must be opened. Paths are relative to the 2026.9.29 layout.

| Symptom | First file to open |
|---|---|
| Precedence / types / environment | `src/dragiter/application/config/configuration_loader.py` |
| Ranges, mandatory keys | `src/dragiter/application/config/configuration_validator.py` |
| `regex_pattern` abort, globs | `src/dragiter/application/pipeline/resource_collector.py` |
| Staged split, pack, cap | `MaterialTokenizer` (application pipeline) |
| `{STDIN}` / `-t` | `PromptCreator`; `tests/test_prompt_creator_stdin.py` |
| What a simulate or live session's content is (board, request) | `src/dragiter/application/pipeline/chat_manager.py`; `tests/test_output_writer_stdout.py` |
| Sink routing, staging workspace, Assembly and commit for stdout / `-o` / `-O` | `src/dragiter/infrastructure/io/workspace_service.py`; `tests/test_staging_workspace.py` |
| Streaming, heartbeat | `src/dragiter/infrastructure/llm/openai_service_ext.py` (streaming only; there is no partial-results mechanism any more) |
| Retry classification | `src/dragiter/infrastructure/llm/openai_runtime.py` |
| Window `n/a` versus `0/0` | `ContextWindowEstimator`; CHANGELOG 2026.9.13 |
| Activity JSONL and masking | `file_activity_logger.py` / `value_settings_activity_provider.py` |

The legacy, non-streaming `OpenAIService` adapter has been deleted from the tree (it was dead code, never wired into the CLI). `httpx` (not `httpx2`) is now a development-only dependency, kept for two test files that build request/response doubles against `openai_service_ext.py`'s retry logic.

---

## 13. Command crib

```bash
# version and man-page summary
dragiter --version
dragiter --info

# always simulate before a live run
dragiter -s -p prompt.toml -r resource.toml -l loop.txt

# live local model with visible board
dragiter -v --tcp-keep-alive -c config-ollama.toml \
  -p prompt.toml -r resource.toml -l loop.txt

# raise or prove the chunk cap
dragiter -s --max-chunks 1 -p prompt.toml -r resource.toml

# pack off (also disables overflow patterns after the first)
dragiter -s --pack-limit-chars 0 -p prompt.toml -r resource.toml

# audit trail
dragiter -s -v -a activity.jsonl -p prompt.toml -r resource.toml

# resume an aborted -O run instead of paying for every session again
dragiter -p prompt.toml -r resource.toml -l loop.txt -O out -m w --resume

# user config
mkdir -p ~/.config/dragiter
cp config-ollama.toml ~/.config/dragiter/config.toml
```

---

*End of FAQ. Not a substitute for `docs/manual.md` or `docs/reference.md`.*
