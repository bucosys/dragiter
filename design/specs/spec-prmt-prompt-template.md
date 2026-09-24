# Prompt template — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-prmt-prompt-template.md` |
| Code | `PRMT` |
| Type | functional |
| Version | 0.2 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | `MATL`, `CHNK`, `LOOP` |

## 1. Purpose

The prompt template and its placeholders, filled for every request with material and loop values.

## 2. Scope

### In scope

- The two mutually exclusive prompt sources: `-t`/`--task` (inline synthesis) and `-p`/`--prompt-file` (TOML file).
- The TOML file's four sections — `[system]`, `[task]`, `[behaviour]`, `[outcome]` — and their fields (`instruction`, `first`, `material`, `synthesis`, `temperature`, `sequential_processing`, `output_filename_schema`, `output_delimiter`).
- Default values applied when `[behaviour]`/`[outcome]` keys are absent from the file.
- Precedence of an explicitly-set CLI flag over the same value coming from the prompt file.
- The stdin contract: stdin is read only when `-t` is used, or when `task.first` contains the `{STDIN}` placeholder — never eagerly.
- The placeholder vocabulary available in `material` (`CHUNK_*`) and `synthesis` (`LOOP_*`), as produced by `CHNK` and `LOOP` respectively — this document defines which names exist and where their values come from, not how/when they are substituted into a chat message.

### Out of scope

- Sending requests (see `EXEC`).
- Executing the placeholder substitution itself when chat messages are assembled, including the lenient (`{key}`-stays-literal) handling of unresolved `LOOP_*` keys in `synthesis` (see `EXEC`, `MessageBuilder`).
- Where `CHUNK_*` values and loop dictionaries themselves come from (see `MATL`, `CHNK`, `LOOP`).

## 3. Terms

| Term | Meaning |
|---|---|
| Task mode | `-t`/`--task TEXT`: no prompt file: `TEXT` becomes `synthesis`, stdin becomes `first` |
| Prompt-file mode | `-p`/`--prompt-file FILE`: a TOML file provides all four sections |
| `first` | Introductory user message, sent once per session before material/synthesis |
| `material` | Template string formatted per chunk with `CHUNK_*` placeholders (see `CHNK`) |
| `synthesis` | Template string formatted per loop entry with `LOOP_*` placeholders (see `LOOP`) |
| `{STDIN}` | Placeholder inside `task.first` that opts into reading stdin in prompt-file mode |

## 4. Behaviour

### 4.1 Source selection

Exactly one of `-t`/`--task` or `-p`/`--prompt-file` selects how the `PromptTemplate` is built; `-t` takes the inline path and never reads a TOML file.

### 4.2 Task mode (`-t`)

`first` = the content read from stdin, `synthesis` = the `-t` text verbatim, `instruction` = `None`, `material` = `None`. `temperature` and `sequential_processing` come from `AIServiceParameters`/`ExecutionParameters` if explicitly set on the CLI, else default to `0.0`/`False`. `output_filename_schema`/`output_delimiter` come from `OutputParameters` if explicitly set, else default to `"dragiter-out.txt"`/`"\n"`.

### 4.3 Prompt-file mode (`-p`)

The TOML file's `[system]` and `[task]` sections are read directly into `instruction`/`first`/`material`/`synthesis`. `[behaviour]` (`temperature`, `sequential_processing`) and `[outcome]` (`output_delimiter`, `output_filename_schema`) start from the same built-in defaults as task mode, then are overwritten by whatever the file's own `[behaviour]`/`[outcome]` tables set. After the file is parsed, any of `--sequential`, `--output-delimiter`, `--output-filename-schema`, `--temperature` that was **explicitly set** on the CLI overwrites the file-derived value for that one field; a CLI flag left at its default never overrides the file.

### 4.4 Stdin contract

Stdin is read in exactly two situations: `-t` is used (always reads exactly once), or `task.first` contains `{STDIN}` in prompt-file mode (reads once, then substitutes). In every other case `PromptCreator` never touches stdin, so a still-open, non-TTY stdin that never reaches EOF cannot hang the process.

### 4.5 Placeholder vocabulary

- `material` is formatted per chunk with `CHUNK_NUM_ID`, `CHUNK_FILE_NAME`, `CHUNK_SECTION_NAME`, `CHUNK_SECTION_NUM_ID`, `CHUNK_CONTENT` (see `CHNK`).
- `synthesis` is formatted per loop entry with whatever keys that entry's dictionary carries, always including `LOOP_NUM_ID`, and `LOOP_CONTENT` for plain-text loop lines (see `LOOP`).
- `task.first` additionally recognises `{STDIN}` (Section 4.4), resolved by `PromptCreator` itself, before any chat message exists.

## 5. Error cases

- Any failure while reading or parsing the prompt (missing file, unreadable file, malformed TOML, a required key missing from `[system]`/`[task]`) is wrapped in `PromptBuilderError`, with the original exception preserved as its cause.
- A `material` placeholder outside the `CHUNK_*` vocabulary (Section 4.5) is **not** tolerated the way an unresolved `synthesis`/`LOOP_*` placeholder is: `Chunk.format_template` uses a plain `str.format_map`, so an unknown key raises `KeyError` when a chat message is built — this surfaces later, outside `PromptCreator`/`PromptBuilderError` (see `EXEC`).

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`PRMT-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

- **PRMT-01** Given `-t "TEXT"` is set, when `PromptCreator` runs, then `first` is the stdin content, `synthesis` is `"TEXT"`, and `instruction`/`material` are `None`.
- **PRMT-02** Given `-t` is set, when `PromptCreator` runs, then stdin is read exactly once.
- **PRMT-03** Given a prompt file without `-t` and without `{STDIN}` in `task.first`, when `PromptCreator` runs, then stdin is never read.
- **PRMT-04** Given a prompt file with `{STDIN}` in `task.first` and non-empty piped stdin, when `PromptCreator` runs, then `first` has the placeholder replaced by that content.
- **PRMT-05** Given a prompt file with `{STDIN}` in `task.first` and no stdin content, when `PromptCreator` runs, then `first` has the placeholder replaced by the empty string, not left literal.
- **PRMT-06** *proposed* Given `-p FILE` whose `[behaviour]`/`[outcome]` tables omit some or all keys, when `PromptCreator` runs, then the omitted fields take the built-in defaults (`temperature=0.0`, `sequential_processing=False`, `output_filename_schema="dragiter-out.txt"`, `output_delimiter="\n"`).
- **PRMT-07** *proposed* Given `-p FILE` and a matching CLI flag (`--sequential`, `--output-delimiter`, `--output-filename-schema`, `--temperature`) explicitly set, when `PromptCreator` runs, then the CLI value overrides the file's value for that field only.
- **PRMT-08** *proposed* Given `material` contains a placeholder outside the `CHUNK_*` vocabulary, when a chat message is built from a chunk, then formatting raises `KeyError` instead of leaving the placeholder literal.

## 7. Open questions

- PRMT-06 through PRMT-08 have no dedicated unit test in the current suite (only `tests/test_prompt_creator_stdin.py` is owned by this pass, and it covers stdin handling only) — a follow-up should add coverage and drop the *proposed* mark.
- Whether an unknown `material` placeholder raising `KeyError` (PRMT-08) is the intended contract, or should instead behave like `synthesis` (leave unresolved placeholders literal), was not decided here — it is simply what the current code does.

## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.2 (2026-09-25): initial version filled in from `prompt_creator.py`, `prompt_template.py` and `tests/test_prompt_creator_stdin.py`.
