# Output — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-outp-output.md` |
| Code | `OUTP` |
| Type | functional |
| Version | 0.2 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | `STAG` (technical; its criteria on output, e.g. STAG-06, stay there and are referred to by identifier) |

## 1. Purpose

Writing results as the user sees it: which sink receives them (`-o` FILE, `-O` DIR, or
stdout), how the final file name is built from `output_filename_schema`, what `-m x|w|a`
means for the user, and what a chunk- or loop-derived name can and cannot do to the
file system.

## 2. Scope

In scope:

- The three sinks (`-o`, `-O`, stdout-only) as user-visible choices — mutually exclusive
  (`-o`/`-O`), see `STAG-06` for the exact rejection.
- `output_filename_schema` and its placeholders (`{CHUNK_NUM_ID}`, `{CHUNK_FILE_NAME}`,
  `{CHUNK_SECTION_NAME}`, `{CHUNK_SECTION_NUM_ID}`, `{LOOP_*}`, `{TIMESTAMP}`) and the
  fallback name used when none of them appear in the schema.
- Sanitisation of any material- or loop-derived value that becomes part of a file name
  or path, so that untrusted content can never escape the target directory or produce
  an illegal file name.
- `-m x|w|a` as a user-facing contract (create-only / overwrite / append); the exact
  transactional mechanics (workspace, shards, rename order, failure handling) are
  `STAG`'s, referenced here by identifier.
- What appears on stdout for a live run and for a simulate run, depending on which
  sink is active.
- Injecting a different `ResultBoardService` implementation for the result board.

Out of scope: The internal staging and commit mechanism (see `STAG`, technical).
Simulate-mode content itself, i.e. what the boards show (see `SIMU`).

## 3. Terms

| Term | Meaning |
|---|---|
| Sink | `-o FILE`, `-O DIR`, or stdout-only (neither given). Exactly one is active. |
| `output_filename_schema` | User-supplied template for `-O` file names (and simulate per-session file names); ignored for `-o`, whose name is always `FILE` (`STAG Section 7.6`). |
| Placeholder | A `{NAME}` token in the schema, resolved from the chunk, the loop entry, or the write timestamp. |
| Fallback name | The name used when the schema contains none of the known placeholders: `session_<NNNN>.md` when a session index is known, otherwise `output.md`. |
| Sanitised component | A placeholder value with path separators, `..`, control characters and reserved characters removed or replaced, then length-capped. |
| Result board | The Markdown output produced for a simulate run (`ResultBoardService.run_board` / `session_board` / `payload_table`); the default implementation is `MarkdownResultBoard`. |

## 4. Behaviour

### 4.1 Sinks

- `-O DIR`: one final file per chat session, named from `output_filename_schema`.
- `-o FILE`: exactly one final file, always named `FILE`; the schema does not apply to
  the file name itself (only to `{TIMESTAMP}`/`{CHUNK_*}`/`{LOOP_*}` if used elsewhere,
  which it is not for `-o`).
- Neither flag: stdout-only. A live run's replies are echoed to stdout exactly when no
  file sink is active (OUTP-08 to OUTP-10); a simulate run's board goes to stdout under
  the same condition (OUTP-11, OUTP-12).
- `-o` and `-O` together are rejected before any path is touched (`STAG-06`).

### 4.2 Filename schema and placeholders

`output_filename_schema` is filled in by `infrastructure/io/filename_utils.py:format_output_filename`:

- Chunk placeholders (`{CHUNK_NUM_ID}`, `{CHUNK_FILE_NAME}`, `{CHUNK_SECTION_NAME}`,
  `{CHUNK_SECTION_NUM_ID}`) are available whenever the session carries a chunk.
- Loop placeholders come from the loop entry's dict: any key ending `_NUM_ID` (or
  exactly `LOOP_NUM_ID`) is coerced to an integer (falling back to the session index),
  numeric values pass through unchanged, everything else is sanitised as text.
  `LOOP_ID` defaults to `"unknown"` if the loop entry does not supply one.
- `{TIMESTAMP}` is filled by the caller: the shard's filesystem mtime at commit
  (`STAG-10`, `STAG-26`) for `-O`, or the write-time clock for simulate boards
  (`OutputWriter._format_filename`, which never has a shard to date itself from).
- If the schema contains none of `CHUNK_`, `LOOP_`, `TIMESTAMP`, the fallback name is
  used instead of applying the template at all (OUTP-01).
- Every resolved value passes through `sanitize_filename` before assembly, and the
  fully formatted name is sanitised again as a whole (OUTP-02 to OUTP-06).
- `ensure_path_within_directory` is a second, independent check applied to the final
  path under `-O`, so that even a schema that reintroduces a separator cannot place a
  file outside the target directory (OUTP-07).

### 4.3 Write modes

`-m x` (create-only), `-m w` (overwrite) and `-m a` (append) describe what the user
sees at the target path once the run succeeds; `STAG Sections 7.1–7.3` define exactly
how a rename, a replace or a delimiter-joined append is carried out and what happens
on the first failure. `-m` has no effect on stdout-only (`STAG Section 7.9`).

### 4.4 Result board injection

`OutputWriter` is constructed with a `ResultBoardService` (default `MarkdownResultBoard`);
any implementer can be substituted at the composition root, replacing both the run
board and the per-session board without changing `OutputWriter` itself (OUTP-13).

## 5. Error cases

- A material- or loop-derived value that would traverse out of the target directory,
  contain a path separator, or use a reserved/control character never reaches the file
  system unsanitised — it is neutralised into a safe component instead of raising
  (OUTP-02 to OUTP-04). Path escape after sanitisation is rejected with `ValueError`
  by `ensure_path_within_directory` (OUTP-07) rather than silently corrected.
- A schema using `{TIMESTAMP}` without a timestamp supplied by the caller is a
  programming error (`ValueError`), not a user-facing case in normal operation — the
  caller always supplies one when the schema needs it.
- All remaining error cases (missing/unwritable sink parents, commit collisions,
  transfer failures) belong to `STAG Section 9`.

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`OUTP-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

### Filename schema and sanitisation

- **OUTP-01** Given a schema with none of `{CHUNK_*}`, `{LOOP_*}`, `{TIMESTAMP}`, when a
  file name is formatted, then the fallback name is used (`session_<NNNN>.md` with a
  known session index, otherwise `output.md`) instead of the literal schema text.
- **OUTP-02** Given a chunk file name containing path-traversal sequences or separators,
  when it is used as `{CHUNK_FILE_NAME}`, then the resulting file name contains no `/`,
  `\` or `..` and no unsanitised traversal fragment.
- **OUTP-03** Given a loop entry whose values contain path-traversal sequences, when they
  are substituted into the schema, then the resulting name contains no `/`, `\` or `..`.
- **OUTP-04** Given a raw name with control characters, reserved characters
  (`<>:"|?*`), or that is empty/whitespace-only/`.`/`..`, when it is sanitised, then the
  forbidden characters are removed and an empty result falls back to `"output"`.
- **OUTP-05** Given a sanitised name longer than the configured maximum length, when it
  is truncated, then the result does not exceed that length and keeps its extension
  where one can be preserved.
- **OUTP-06** Given `None` or an empty/whitespace-only raw name, when it is sanitised,
  then the result is the fallback `"output"`.
- **OUTP-07** Given a candidate path built from a sanitised name, when it is checked
  against the target directory, then a path that would still resolve outside that
  directory is rejected with `ValueError`, and a path that resolves inside it is
  accepted unchanged.

### stdout behaviour

- **OUTP-08** Given a live (non-simulate) run and neither `-o` nor `-O`, when the run
  completes, then the reply text is echoed to stdout.
- **OUTP-09** Given a live run and `-o FILE`, when the run completes, then nothing is
  echoed to stdout; the reply is only in `FILE`.
- **OUTP-10** Given a live run and `-O DIR`, when the run completes, then nothing is
  echoed to stdout; the reply is only in the directory.
- **OUTP-11** Given a simulate run and neither `-o` nor `-O`, when the run completes,
  then the run board is printed to stdout.
- **OUTP-12** Given a simulate run and `-o FILE`, when the run completes, then the run
  board is written to `FILE` and nothing is printed to stdout.

### Result board injection

- **OUTP-13** Given a `ResultBoardService` implementation other than
  `MarkdownResultBoard` is passed to `OutputWriter`, when a simulate run completes, then
  the injected implementation's output appears instead of the default Markdown board.

## 7. Open questions

- Whether a dedicated `OUTP-NN` should cover `-m` semantics directly, or whether
  referring to `STAG Sections 7.1–7.3` throughout remains sufficient once a user-facing
  regression test exists at this level.
- Whether the fallback name (`session_<NNNN>.md` / `output.md`) should be configurable
  rather than fixed.

## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.1 (2026-09-25): internal cleanup — OutputWriter/ResultBoardService now require real ContextValidationReport/Resources instances (no behaviour change).
- 0.2 (2026-09-25): initial version. Purpose, scope, terms, behaviour, error cases and
  acceptance criteria OUTP-01 to OUTP-13 added, derived from
  `application/pipeline/output_writer.py`, `infrastructure/io/filename_utils.py` and
  `domain/ports/result_board_service.py`. Deliberately excludes STAG's internal
  mechanics, referenced by identifier instead.
