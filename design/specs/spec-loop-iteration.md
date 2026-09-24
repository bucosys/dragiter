# Iteration — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-loop-iteration.md` |
| Code | `LOOP` |
| Type | functional |
| Version | 0.2 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | `PRMT`, `EXEC` |

## 1. Purpose

Running over the entries of a loop file: one request per entry or chunk, order and selection of entries.

## 2. Scope

### In scope

- The optional loop file (`--loop-file`/`-l`): reading it into a sequence of placeholder dictionaries.
- The 50-item hard limit and its abort message.
- Per-line parsing: JSON object → dictionary entry; anything else (invalid JSON, or valid JSON that is not an object) → plain-text fallback entry.
- `LOOP_NUM_ID`: the entry's 1-based position, assigned regardless of parse path.
- The `LOOP_CONTENT` key produced for plain-text/non-object entries, and the `LOOP_ID` key a JSONL object may itself supply.
- Behaviour when no loop file is given at all (zero entries).

### Out of scope

- Content of the prompt, `synthesis` and its placeholder syntax (see `PRMT`).
- How a loop entry combines with a chunk into a chat session, sequential vs. batched chunk iteration (see `EXEC`, `MessageBuilder`).

## 3. Terms

| Term | Meaning |
|---|---|
| Loop file | Text file named by `--loop-file`/`-l`; one entry per non-blank line |
| Entry / line | One resulting placeholder dictionary, one per non-blank loop-file line |
| JSONL line | A loop-file line that parses as a JSON object; its keys become the entry directly |
| Plain line | A loop-file line that is not a JSON object (invalid JSON, or valid JSON of another type); becomes `{"LOOP_CONTENT": line, "LOOP_NUM_ID": index}` |
| `LOOP_NUM_ID` | The entry's 1-based position in the file, after blank lines are dropped; always present, on both parse paths |
| `LOOP_CONTENT` | The raw line text; present on plain lines, and on any JSONL object that happens to define it itself |
| `LOOP_ID` | Not produced by `LoopBuilder`; an optional key a JSONL object may supply itself, preferred over `LOOP_CONTENT` by some consumers (see `SIMU`) |
| Hard limit | `LoopBuilder.MAX_LOOP_ITEMS` = 50 non-blank lines per run |

## 4. Behaviour

### 4.1 No loop file

When `--loop-file` is not set, `LoopBuilder` returns a `Loop` with an empty entry list — no error, no iteration; the rest of the pipeline runs its no-loop path (see `EXEC`).

### 4.2 Reading the file

When set, the file is read into stripped lines; blank lines (empty after stripping) are dropped before counting or parsing — they never occupy a `LOOP_NUM_ID` slot and never count toward the hard limit.

### 4.3 Hard limit

More than 50 non-blank lines abort the run before any request is built or sent, with an actionable message naming the actual count and the limit, and suggesting the file be split. Exactly 50 is accepted. The limit applies identically whether lines are plain text or JSONL objects.

### 4.4 Per-line parsing

Each non-blank line is parsed as JSON:

- Parses to a JSON **object** → that object's own key/value pairs become the entry, and `LOOP_NUM_ID` (the line's 1-based position) is added (overwriting any same-named key the object already had).
- Fails to parse, or parses to a JSON value that is **not** an object (number, string, list, boolean, `null`) → the entry falls back to `{"LOOP_CONTENT": <line>, "LOOP_NUM_ID": <index>}`.

`LOOP_NUM_ID` is therefore always present, on both paths, and always reflects the line's own position — never a count of only-JSONL or only-plain-text lines.

### 4.5 `LOOP_ID` vs. `LOOP_CONTENT`

`LoopBuilder` itself never sets `LOOP_ID`. A JSONL object is free to define its own `LOOP_ID`; some downstream consumers (e.g. the simulate session board, see `SIMU`) display `LOOP_ID` when present and fall back to `LOOP_CONTENT` otherwise.

## 5. Error cases

- The loop file cannot be read (missing, unreadable) → wrapped in `LoopBuilderError`, naming the loop file's own path.
- More than 50 non-blank lines → `LoopBuilderError`, Section 4.3.

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`LOOP-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

- **LOOP-01** Given no loop file is set, when `LoopBuilder` runs, then it returns a `Loop` with an empty `lines` list and raises no error.
- **LOOP-02** Given a loop file with blank lines interspersed among 50 non-blank lines, when `LoopBuilder` runs, then the blank lines are dropped and do not count toward the hard limit.
- **LOOP-03** Given a loop file with exactly 50 non-blank lines, when `LoopBuilder` runs, then all 50 become entries and no error is raised.
- **LOOP-04** Given a loop file with 51 or more non-blank lines, when `LoopBuilder` runs, then it aborts with `LoopBuilderError` naming the actual count and the hard limit (50), before any request is built.
- **LOOP-05** Given a loop file with more than 50 valid JSONL objects, when `LoopBuilder` runs, then the same hard limit applies as for plain-text lines.
- **LOOP-06** Given a loop-file line that parses as a JSON object, when `LoopBuilder` runs, then that object's own keys become the entry, with `LOOP_NUM_ID` set to the line's 1-based position.
- **LOOP-07** Given a loop-file line that is not valid JSON, or is valid JSON that is not an object, when `LoopBuilder` runs, then the entry is `{"LOOP_CONTENT": line, "LOOP_NUM_ID": index}`.
- **LOOP-08** Given a loop file that cannot be read, when `LoopBuilder` runs, then the wrapping `LoopBuilderError` names the loop file's own path, not any other setting's path.

## 7. Open questions

*None yet.*

## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.2 (2026-09-25): initial version filled in from `loop_builder.py`, `loop.py`, and read-only review of `tests/test_circuit_breakers.py` (not owned by this pass).
- 0.3 (2026-09-25): LOOP-01/06/07 covered by new `tests/test_loop_builder.py`; *proposed*
  marks dropped. Fixed the `LoopBuilderError` copy-paste bug (it named
  `prompt_file_path_setting` instead of `loop_file_path_setting`) and added LOOP-08 as a
  regression criterion.
