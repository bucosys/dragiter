# dragiter Glossary

**Version:** derived from source (2026.9.26)  
**Language:** British English  
**Audience:** readers of the Manual, the Technical Reference and the FAQ  
**Scope:** Product words. Not a procedure guide and not a flag list.  
**Sources:** `docs/manual.md`, `docs/reference.md`, `docs/info.txt`, `CHANGELOG.md`, `README.md`, example READMEs, and the 2026.9.13 tree

Each entry is the meaning the program actually uses. Board labels are quoted exactly as they appear on stdout and in simulate files. When this page disagrees with the Manual or the Technical Reference, name the file and the version and treat this page as uncertain.

British English is used throughout.

---

## How to extend this page

Add a new `###` heading in **alphabetical order**. Do not rename an existing heading: MkDocs permalinks follow the heading text.

Keep one word or tight phrase per heading. Write, in this order:

1. One-sentence definition
2. What it is *not*
3. Pointer to Manual versus Reference

Do not introduce admonition syntax, tabbed fences or other Material extras — `mkdocs.yml` currently enables only `search` and `privacy`.

To publish on the site, copy this file next to `manual.md` / `reference.md` (CI already copies `docs/*.md` into `web/`) and add one nav entry in `mkdocs.yml`:

```yaml
nav:
  - Home: index.md
  - Manual: manual.md
  - Reference: reference.md
  - FAQ: faq.md
  - Glossary: glossary.md
```

---

## Terms

### Activity log

A JSON Lines trace of one run, appended when an activity file is requested. Each record carries a UTC timestamp and the producer class. Fields whose names contain the substring `key` are masked.

It is not the run board and not the model reply.

See Manual, Activity logging. See Reference §10.

### Batched

Board label `mode batched`. All **valid** chunks of one loop line are placed in a **single** chat request. The system instruction and the introductory `first` text appear once; each valid chunk becomes its own user message from the `material` template; `synthesis` appears once. Without a loop file there is one such request. With a loop file there is one request **per line**, each still holding every valid chunk.

It is not “ask the same question once per chunk”. That is sequential mode. It is not packing. It is not a provider batch API and not parallel calls. The board word in 2026.9.13 is `batched`, not `combined`.

See Manual, Sequential versus batched processing. See Reference §9.

### Character estimate

Token size used by the window check: the character length of every message in the session, divided by `chars_per_token`, then truncated to an integer. The board cell `tokens` is that input estimate **plus** the reserved output budget.

It is not a vendor tokenizer and not `chars / chars_per_token` on the raw chunk alone.

See Manual, How to keep requests inside the model’s context window. See Reference §9.

### Chunk

One piece of material after the staged split, optional substitutions, optional packing, and include/exclude filters. A chunk belongs to one file and one resource section. It is either valid or invalid.

It is not a chat session and not a loop line.

See Manual, Material, chunks and the context window. See Reference §6.

### Chunk substitutions

An optional, ordered rewrite of each piece **after** the first split and **before** packing and filters. Replacements are literal: back-references in the replacement string are ordinary characters.

It is not a second split and has no command-line override.

See Manual, How to define material. See Reference §6. See CHANGELOG 2026.9.13.

### Circuit breaker

A hard stop that aborts the run: 100 MB per input file, 200 chunks unless the cap is raised, 50 loop lines. Soft size notes (very short or very large pieces) warn and continue.

It is not the context-window refusal, which is a separate check.

See Manual, Hard safety limits. See Reference §2.

### Combined

Informal synonym for **batched**. It does **not** appear on the 2026.9.13 board. Do not write it in commands, snapshots or support answers that quote stdout.

See [Batched](#batched).

### Context window

The model’s input-plus-output budget. dragiter enforces it only when `chars_per_token`, `max_context_tokens` and `max_output_tokens` are all set. A request whose estimated input plus reserved output exceeds `max_context_tokens` is refused before the network — except in simulation, which records a warning and still prints the board.

It is not packed character count.

See Manual, How to keep requests inside the model’s context window. See Reference §2 and §9.

### First

The introductory user text of a prompt template (`task.first`). It is sent once per session, before the material messages.

It is not the system instruction and not the question in `synthesis`.

See Manual, How to write a prompt template. See Reference §5.

### Loop

A list of variants. Plain text: one non-empty line becomes `LOOP_CONTENT`. JSON Lines: each object’s keys become placeholders. The whole prompt runs once per line. More than 50 lines abort.

An empty list is shown as `loops 0` on the run board. Session count still uses an implicit factor of one.

See Manual, How to iterate over many items. See Reference §7.

### Material

The texts the model should see, collected from resource sections, split into chunks, then injected through the `material` template.

It is not the prompt’s question and not the loop file.

See Manual, How to define material. See Reference §6.

### Pack

Joining consecutive chunks **of the same file** after the split, until a character budget would be exceeded. Packing never crosses a file or a section. Valid and invalid chunks are not packed together. A piece that no remaining pattern can shrink stays whole.

Board `pack` is that effective budget, or `off`, or `mixed`. It is not batched mode.

See Manual, How to define material. See Reference §6.

### Pack from

Origin of the effective pack budget on the board: `cli` when a global value is set (including `0`), `section` when one shared positive section budget applies, `mixed` when section budgets differ, `off` when nothing positive is set.

`mixed` and `off` make the run-board `over` count zero.

See Reference §9.

### Partial results

Mid-run workspace beside `-o` or `-O`: `.tmp_staging_file_<PID>` plus the target suffix, or `.tmp_staging_dir_<PID>/`. Created after the `-m x` check and before the first completion. Removed after a successful commit. Left in place if a later call fails.

They are not the final routed result. `.dragiter-partial/` is gone.

See Reference §1a. See CHANGELOG Unreleased.

### Peak

On the run board, `peak / limit` is the largest session total (estimated input plus reserved output) against `max_context_tokens`. `peak at` is the 1-based session index of that maximum. Until the window trio is complete both peak and limit show `--`.

`peak` is not the sum of all sessions and not the raw character total.

See Reference §9. See CHANGELOG 2026.9.13.

### Placeholder

A `{NAME}` token in a template. Recognised names include chunk fields, loop fields, JSONL keys and `{STDIN}`. Unknown names stay visible in the text.

Placeholders are not expanded inside chunk-substitution replacements.

See Reference §5.

### Prompt template

The versioned instruction set: system role, `first` / `material` / `synthesis`, optional behaviour and outcome. Same inputs yield the same request payload.

It is not a chat history and not provider configuration.

See Manual, How to write a prompt template. See Reference §5.

### Provider

Any OpenAI-compatible chat-completions endpoint. Switching provider means changing the base URL, the model name and, when required, the API key.

dragiter is not a model host and not a vendor SDK wrapper beyond that contract.

See Manual, How to connect. See Reference §1a.

### Resource section

One named block in the resource file: where to search, which files match, how to split, whether to pack, which filters and substitutions apply.

Sections do not share packing across their boundary.

See Reference §6.

### Run board

The four-column simulate summary: sessions, mode, chunks/files, valid/loops, chars, pack, small/over, window, peak, output. On stdout only when neither a result file nor a result directory is set. With a result file the run board is written once at the top of that file.

It does not print payloads. Those belong in session files after a session board.

See Manual Tutorial step 2. See Reference §9.

### Sequential

Board label `mode sequential`. Each **valid** chunk is its own chat request. A loop file multiplies that count. Invalid chunks create no session.

It is not “calls run one after another” in the networking sense; combined requests also run one after another.

See Manual, Sequential versus batched processing. See Reference §9.

### Session

One assembled chat request: system, `first`, one or more material messages, synthesis. `sessions` on the run board is the number of such requests.

It is not a chunk and not a saved conversation across runs. There is no hidden session state.

See Reference §9.

### Session board

The per-request header written into simulate output files: session index, mode, file, chunk, section, valid, chars, tokens, pack, loop. Under a result directory each file starts with this header, then the transcript. It does not appear on stdout when no file sink is set.

See Manual Tutorial step 2. See Reference §9.

### Simulate

A full assembly of material, templates and routing with no network call and no token spend. The board and, when a file sink is set, the prompt transcripts are the product.

It is not a syntax-only parse. Window overflow warns instead of aborting.

See Manual Tutorial step 2. See Reference §9.

### Small / over

Run-board pair. `small` counts final chunks shorter than 50 characters. `over` counts final chunks longer than the **effective pack budget**. When pack is `off` or `mixed`, `over` is 0.

There is no 20 000-character warning in the 2026.9.13 tokenizer. Manual and Reference follow that fact.

See Reference §9. See `MaterialTokenizer.count_size_flags` in 2026.9.13.

### Staging

Typed workspace beside the user-chosen sink: `.tmp_staging_file_<PID><suffix>` for `-o`, `.tmp_staging_dir_<PID>/` for `-O`. Completions write there first. `-m` runs only at commit. The visible target bytes must match a direct `-m` write with no workspace.

See Reference §9. See CHANGELOG Unreleased.

### Stdin

Read only when a task is supplied on the command line or when `{STDIN}` appears in `task.first`. A pipe into a template that asks for neither is ignored.

See Reference §5. See CHANGELOG 2026.9.9.

### Stdout contract

Results (live replies, or the simulate run board) appear on stdout only when neither a result file nor a result directory is set. File routing replaces that sink. Shell redirection is not treated as a file sink. Progress (`-v`) writes to stderr.

See Reference §9. See README stdout contract.

### Synthesis

The task or question at the end of a session (`task.synthesis`). Loop placeholders belong here. In batched mode it is sent once per request, after every material message of that request.

See Manual, How to write a prompt template. See Reference §5.

### System instruction

The persona text (`system.instruction`), sent as the system message of every session.

See Reference §5.

### Valid chunk

A chunk that passed include/exclude filters. Only valid chunks enter prompts. Sequential mode skips invalid chunks. Batched mode injects only valid ones. Valid and invalid chunks are never packed together.

A filter that marks almost everything invalid can still “run” and leave `file none` and raw `{CHUNK_*}` placeholders.

See Reference §6. See CHANGELOG 2026.8.20.

### Verbose board

Live progress on stderr: a start block, one request line per completion with a pulse mark, a closing block. With `-o` or `-O`, completions also land in the typed staging workspace beside the target. The board is never written onto the result sink.

CHANGELOG 2026.9.13 writes the closer prefix as `■`; Reference §1a writes `□`. Treat the family start / pulse / box as the contract.

See Reference §1a. See CHANGELOG 2026.9.13.

### Warns

The run-board count `peak at / warns`. `warns` is the number of **window-overflow** notes recorded in simulation. Short-chunk log lines do not increment it.

See Reference §9. See `ContextWindowEstimator` in 2026.9.13.

### Window

Run-board word: `yes`, `no` or `n/a`. `n/a` means the three window settings are not all present — not a successful estimate of zero. From 2026.9.13 that state is `n/a` and `-- / --`, not `yes` and `0 / 0`.

See Reference §9. See CHANGELOG 2026.9.13.
