# Material — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-matl-material.md` |
| Code | `MATL` |
| Type | functional |
| Version | 0.2 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | `CHNK`, `LIMT` (hard size limits) |

## 1. Purpose

Providing material: defining resources in the resource file, resolving glob patterns to files under a base directory, detecting file encoding, and reading file content — the raw text every chunk is later built from.

## 2. Scope

### 2.1 In scope

- The resource file format: one TOML table per resource section (`glob_patterns`, `base_directory`, `pack_limit_chars`, `regex_patterns`, `exclude_filters`, `include_filters`, `chunk_substitutions`).
- Resolving `glob_patterns` against `base_directory`, including the absolute-pattern escape hatch and containment checks for relative patterns.
- Storing a resource section's settings (pack limit, regex patterns, substitution rules) so later stages (`CHNK`) can use them, and reflecting them in the activity log.
- File encoding detection and file reading as a `TextFile`.

### 2.2 Out of scope

- Splitting file content into chunks, staged regex, filters applied to chunk content, packing (see `CHNK`).
- The 100 MB per-file read limit and other hard resource limits (see `LIMT`).
- The removed singular resource key: rejecting it is in scope here (Section 5); anything about chunk content is not.

## 3. Terms

| Term | Meaning |
|---|---|
| Resource section | One `[name]` table in the resource TOML file; becomes one `ResourceSection` |
| Base directory | The directory relative glob patterns are resolved and contained against (`base_directory` key, or `--base-directory`, or CWD as default) |
| Containment | A resolved match must be `base_directory` itself or have it as an ancestor; otherwise it is silently skipped |
| Absolute pattern | A glob pattern that is itself an absolute path; resolved from its own anchor, exempt from containment (an explicit, intentional escape hatch) |
| `TextFile` | A resolved file path plus its detected encoding |
| `chunk_substitutions` | Literal search/replace rules attached to a resource section, applied later during chunking (collected here, applied in `CHNK`) |

## 4. Behaviour

### 4.1 Reading the resource file

`ResourceCollector.run` reads the TOML file named by `--resource-file`/`resource_file` (`InputParameters.resource_file_path_setting`). If unset, it returns an empty `Resources` (zero sections) — this is not an error.

Each top-level table becomes one `ResourceSection` with the file's `glob_patterns` resolved into `TextFile`s, plus `regex_patterns`, `exclude_filters`, `include_filters`, `pack_limit_chars`, and `chunk_substitutions` carried through unchanged for `CHNK` to use.

`base_directory`: the section's own key if given, otherwise the CWD at collection time; `--base-directory` (`WorkspaceParameters.base_directory_path_setting`), when set, rebases it afterward and takes precedence.

A section with no matching files (`glob_patterns` resolves to nothing) is silently omitted — it never becomes an empty `ResourceSection` (see Section 4.2, `if text_files:` guard).

### 4.2 Glob resolution and containment

For each `glob_patterns` entry:
- **Absolute pattern** (`Path(pattern).is_absolute()`): resolved from its own filesystem anchor, no containment check — the resource author named an exact path deliberately.
- **Relative pattern**: resolved against `base_directory`; every match is `resolve()`d and kept only if the resolved path equals `base_directory` or has it as an ancestor. This blocks both `..`-based traversal and a symlink inside `base_directory` that resolves to a target outside it — the check is against the resolved real path, not the glob text.

Matches that fail containment are logged as skipped, not raised as an error — collection continues with the remaining matches.

### 4.3 Encoding and reading

Each surviving path is checked with `FileChecker.detect_encoding` (`SimpleFileChecker`): BOM sniffing first (UTF-8/16/32), then a null-byte binary check, then a decode waterfall over configured candidate encodings (default `utf-8`, `ascii`, `cp1252`, `latin-1`). A path whose encoding cannot be determined, or that fails any check `SimpleFileChecker`/`SimpleTextFileReader` raises for, is silently dropped from the section rather than aborting the whole run (`_check_matches` catches and continues) — see Section 5 for the exception types this can hide.

Reading itself (`TextFileReader.read` / `SimpleTextFileReader`) returns the file's full text at its detected encoding; the 100 MB hard cap on a single file's size is a `LIMT` circuit breaker, not defined here.

### 4.4 Resource key validation

`chunk_substitutions` entries are validated eagerly at collection time (not deferred to `CHNK`): each entry must be a table with a non-empty string `pattern` and a string `replacement`; the whole `chunk_substitutions` value must be a list. Both are reflected verbatim in `Resources.to_activity_dict_list()` for traceability.

## 5. Error cases

| Condition | Result |
|---|---|
| Resource TOML section uses the removed singular key `regex_pattern` | `MaterialCollectorError` naming the section and `regex_patterns` as the replacement |
| `chunk_substitutions` entry missing `pattern` or `replacement`, or with a non-string/empty `pattern` | `MaterialCollectorError` naming the section and index |
| `chunk_substitutions` value is not a list | `ResourceSectionError` (raised when the `ResourceSection` is constructed) |
| Section name is empty or blank | `ResourceSectionError` |
| A matched file cannot be encoding-checked or read (missing, empty, binary, undecodable) | The path is silently dropped from the section; no error surfaces to the caller |
| A relative glob match resolves outside `base_directory` | The match is silently skipped (logged as a warning), not an error |
| Any other unexpected failure while collecting | Wrapped as `MaterialCollectorError` with the original cause preserved (`raise ... from e`) |

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`MATL-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

- **MATL-01** Given a resource section with `pack_limit_chars` set in the TOML file, when it is collected, then `ResourceSection.pack_limit_chars` equals that value and it appears under `sections[].pack_limit_chars` in the activity log.
- **MATL-02** Given a resource section with `regex_patterns` as a list of strings, when it is collected, then `ResourceSection.regex_patterns` preserves the list exactly, and the activity log exposes it under the plural key only (no legacy singular key).
- **MATL-03** Given a resource section using the removed singular key `regex_pattern`, when `ResourceCollector` runs, then it raises `MaterialCollectorError` naming `regex_pattern`.
- **MATL-04** Given a glob match that is a symlink inside `base_directory` resolving to a target outside it, when the section is collected, then that path is excluded from `file_paths` and the real target is never read.
- **MATL-05** Given a relative glob pattern containing `..` aimed outside `base_directory`, when the section is collected, then only files that resolve inside `base_directory` are included.
- **MATL-06** Given a relative glob pattern matching a file nested under `base_directory`, when the section is collected, then that file is included.
- **MATL-07** Given `chunk_substitutions` entries in a resource section, when it is collected, then each rule's `pattern`/`replacement` is stored on the `ResourceSection` and reproduced verbatim in the activity log.
- **MATL-08** Given a `chunk_substitutions` entry with no `pattern` key, when the section is collected, then `ResourceCollector` raises `MaterialCollectorError` naming the section and "no pattern".
- **MATL-09** Given a `chunk_substitutions` value that is not a list, when a `ResourceSection` is constructed, then it raises `ResourceSectionError`.

## 7. Open questions

- `SimpleFileChecker` and `SimpleTextFileReader` have no dedicated unit tests (`BinaryFileError`, `EmptyFileError`, the BOM/encoding waterfall, `TextFileReaderError`) — only indirect e2e coverage. Criteria for these were deliberately left out of Section 6 rather than marked *proposed* for behaviour that already exists; add them once such tests exist.
- Whether a section with zero matched files should be observable in the activity log (currently it is omitted entirely, Section 4.1) is not settled.

## Change history

- 0.2 (2026-09-25): initial body written from the current implementation (`ResourceCollector`, `SimpleFileChecker`, `SimpleTextFileReader`) and its tests.
- 0.1 (2026-09-24): skeleton created.
