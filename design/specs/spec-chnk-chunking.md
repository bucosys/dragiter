# Chunking — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-chnk-chunking.md` |
| Code | `CHNK` |
| Type | functional |
| Version | 0.2 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | `MATL`, `LIMT` (chunk-count hard limit) |

## 1. Purpose

Turning material that has been read (`MATL`) into chunks: staged regex splitting, per-piece substitutions, valid/invalid filtering, and packing pieces together up to a character budget.

## 2. Scope

### 2.1 In scope

- Splitting each file's content with one or more regex patterns, applied in stages.
- `chunk_substitutions`: literal replacement rules applied to a split piece, after splitting and before filtering/packing.
- `valid`/`invalid` classification of a piece via `exclude_filters` / `include_filters`.
- Packing consecutive same-validity pieces of one file together under `pack_limit_chars` (global CLI setting or per-section fallback).
- Renumbering (`num_id`, `section_num_id`) after packing.

### 2.2 Out of scope

- Reading files and defining resources (see `MATL`).
- The 200-chunk total hard limit and its abort behaviour (see `LIMT`).

## 3. Terms

| Term | Meaning |
|---|---|
| Piece | Intermediate string produced by splitting, before it becomes a `Chunk` |
| Staged regex | `regex_patterns`, applied in order: pattern 1 always runs; pattern 2+ only refines a piece that is still over `pack_limit_chars` after the previous stage |
| `chunk_substitutions` | Ordered literal search/replace rules, applied to each split piece before validity filtering and packing |
| Valid | A piece that passes `exclude_filters` (none match) and `include_filters` (at least one matches, if any are configured) |
| Packing | Greedily joining consecutive same-file, same-`valid` pieces with `\n\n` while the combined length stays within `pack_limit_chars` |
| `pack_limit_chars` | Character budget for packing and for staged-regex overflow refinement; `0` or unset disables packing/staging for that scope |

## 4. Behaviour

### 4.1 Staged split

`_split_staged` applies `regex_patterns[0]` to the file's raw content (`_split_on_regex`: cuts at each match start, the matched text stays attached to the start of the following piece; capturing groups are ignored). If no `pack_limit_chars` is in effect, or there is only one pattern, splitting stops there. Otherwise every resulting piece longer than the limit is recursively refined with `regex_patterns[1]`, then `[2]`, and so on, until it fits or patterns are exhausted; a pattern that has no effect on a piece is skipped over without consuming a level. Splitting always runs on the **raw** file text — `chunk_substitutions` are not applied yet at this point.

### 4.2 Substitutions

Each split piece then has every `chunk_substitutions` rule applied in order, literally (`\1`-style backreferences in the replacement are not interpreted — `re.sub` receives a static replacement string, never a pattern-derived one). A rule may replace with an empty string. A piece that becomes empty or whitespace-only after substitution is dropped entirely and never becomes a `Chunk`.

### 4.3 Validity

`_is_content_valid` runs on the **substituted** text: `exclude_filters` are checked first (case-insensitive, multiline) — any match makes the piece invalid, vetoing everything else. Only if none exclude it are `include_filters` checked, if configured: at least one must match, or the piece is invalid. No `include_filters` means everything not excluded is valid.

### 4.4 Effective pack limit

Per resource section: `ExecutionParameters.pack_limit_chars_int_setting` (CLI/global), when explicitly set, always wins — including the value `0`, which disables packing for every section regardless of that section's own `pack_limit_chars`. Only when the global setting is unset does the section's own `pack_limit_chars` (from `MATL`) apply; a section value of `0` or unset also means no packing.

### 4.5 Packing

Packing only runs when an effective limit is in effect and a file produced more than one piece. Two greedy strategies are computed — forward (left to right) and backward (right to left) — each joining consecutive pieces of the same `valid` flag with `\n\n` while staying within the limit; pieces of different `valid` flags, or from different files, are never combined. The strategy producing fewer packs (ties broken by the larger minimum pack size) is kept. Packing never splits a single piece that is already over the limit by itself — an oversized piece is kept whole.

### 4.6 Numbering

After all sections are processed, `num_id` is a single count across every produced piece/pack (1-based, in file/section order); `section_num_id` restarts at 1 within each source file.

### 4.7 Chunk placeholders and reporting

`Chunk.format_template` exposes `CHUNK_NUM_ID`, `CHUNK_FILE_NAME`, `CHUNK_SECTION_NAME`, `CHUNK_SECTION_NUM_ID`, `CHUNK_CONTENT` for use in prompts and output filenames (see `PRMT`, `OUTP`). `MaterialTokenizer.count_size_flags` classifies final chunks as "small" (below `WARN_MIN_CHARS` = 50 characters) or "oversize" (above the effective `pack_limit_chars`, when one is set) purely for informational logging — this never changes which chunks are produced.

## 5. Error cases

| Condition | Result |
|---|---|
| An entry in `regex_patterns` does not compile | `MaterialTokenizerError` naming the section and the pattern's index |
| An entry in `chunk_substitutions` does not compile | `MaterialTokenizerError` naming the section and the index (`Invalid chunk_substitutions[N] in section '…'`) |
| Total produced chunks exceed the effective chunk-count cap | `MaterialTokenizerError`; see `LIMT` for the cap itself |
| Any other unexpected failure while tokenizing | Wrapped as `MaterialTokenizerError`, cause preserved |

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`CHNK-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

### Packing

- **CHNK-01** Given no `pack_limit_chars` in effect, when a file splits into two lines, then each line becomes its own chunk, unmerged.
- **CHNK-02** Given `pack_limit_chars = 0` (global or section), when splitting, then no merge occurs.
- **CHNK-03** Given a limit large enough for two adjacent lines combined, when packing, then they become one chunk, content joined by `\n\n`.
- **CHNK-04** Given a single piece already larger than the limit, when packing, then it is kept whole, never cut.
- **CHNK-05** Given two different files, when packing, then their pieces are never merged into one chunk.
- **CHNK-06** Given the global pack-limit setting is unset and the section defines its own `pack_limit_chars`, when tokenizing, then the section's limit applies.
- **CHNK-07** Given the global pack-limit setting is explicitly `0` and the section defines its own `pack_limit_chars`, when tokenizing, then the global `0` overrides and packing is disabled.
- **CHNK-08** Given the global pack-limit setting is explicitly set to a value smaller than the section's own, when tokenizing, then the global value is the one applied.
- **CHNK-09** Given `exclude_filters` make some pieces of a file invalid and others valid, when packing, then valid and invalid pieces are never combined into the same chunk.
- **CHNK-10** Given packing merges pieces, when chunks are produced, then `num_id`/`section_num_id` are renumbered sequentially starting at 1.

### Staged regex

- **CHNK-11** Given a splitting regex pattern with no capturing group, when splitting, then the matched delimiter text stays attached to the start of the following piece.
- **CHNK-12** Given a `pack_limit_chars` and two staged regex patterns, when a piece from pattern 1 still exceeds the limit, then pattern 2 is applied to refine only that oversized piece.
- **CHNK-13** Given two staged regex patterns but no `pack_limit_chars` in effect, when splitting, then only pattern 1 runs and later patterns are never applied.
- **CHNK-14** Given two staged regex patterns and a limit that no piece exceeds, when splitting, then later patterns are never applied.
- **CHNK-25** Given the shipped Example 04 profile and its resource TOML, when tokenized with its configured section budget, then pattern 1 alone leaves at least one piece over budget and pattern 2 is applied to it (both `pattern 1/2` and `pattern 2/2` are logged), and the resulting chunk count differs from splitting with packing disabled.

### `chunk_substitutions`

- **CHNK-15** Given no `chunk_substitutions` configured, when a piece is produced, then its content is exactly the split text, unchanged.
- **CHNK-16** Given a substitution rule collapsing a run of characters, when applied, then the matched run in the chunk content is replaced.
- **CHNK-17** Given a substitution rule with an empty replacement, when applied, then the matched text is deleted from the chunk content.
- **CHNK-18** Given two substitution rules, when both are applied, then the second rule operates on the first rule's result, not the original text.
- **CHNK-19** Given a substitution replacement containing `\1`, when applied, then it appears literally in the output, never as a backreference.
- **CHNK-20** Given a substitution rule that reduces a piece to only whitespace, when applied, then that piece is discarded and produces no chunk.
- **CHNK-21** Given an invalid `chunk_substitutions` regex pattern, when tokenizing, then `MaterialTokenizerError` names the section and the rule's index.
- **CHNK-22** Given a substitution rule that shortens a piece, when the effective pack limit is evaluated, then it is evaluated against the substituted (post-replacement) length, not the raw split length.
- **CHNK-23** Given `exclude_filters`/`include_filters` and a substitution rule, when validity is decided, then the filters are evaluated against the substituted text, not the raw split text.
- **CHNK-24** Given a splitting regex pattern and a substitution rule that would also match the delimiter, when splitting runs, then it operates on the raw text — the substitution has not been applied yet at split time.

## 7. Open questions

- Overlapping chunk ranges (mentioned as a future direction in the original purpose note) are not implemented and have no criteria here.
- The interaction between `CHNK-25`-style staged-regex overflow and the `LIMT` chunk-count cap on the same shipped example is exercised together in `tests/test_example_04_staged_regex.py`, but the cap itself is specified under `LIMT`, not here.

## Change history

- 0.2 (2026-09-25): initial body written from the current implementation (`MaterialTokenizer`, `Chunk`) and its tests.
- 0.1 (2026-09-24): skeleton created.
