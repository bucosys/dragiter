# Context window and hard limits — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-limt-limits.md` |
| Code | `LIMT` |
| Type | functional |
| Version | 0.2 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | `EXEC`, `CHNK`, `SIMU` |

## 1. Purpose

Estimating the size of every request in advance, keeping to the context window, and
aborting before costs arise (circuit breakers).

## 2. Scope

In scope:

- Estimating input tokens per chat session and comparing the total (input + reserved
  output) against `max_context_tokens` before any request is sent
  (`ContextWindowEstimator`).
- The "not applicable" case when token settings are not fully configured.
- Live vs. simulate behaviour on an over-limit session (abort vs. warning).
- Hard, non-negotiable circuit breakers unrelated to token math: maximum source-file
  size, maximum total chunk count, maximum loop-item count.

Out of scope: Retries after a failed request (see `EXEC`); how chunks or loop items
themselves are produced (see `CHNK`, `LOOP`); how a simulate run reports these numbers
on its boards (see `SIMU`).

## 3. Terms

| Term | Meaning |
|---|---|
| Context validation report | `ContextValidationReport`, produced once per run by `ContextWindowEstimator` before `ChatManager` runs. |
| Not applicable | `chars_per_token`, `max_context_tokens` and `max_output_tokens` are not *all* set. The report still carries real values, but `is_valid`, `max_tokens_limit` and `max_session_tokens` are `None` — a legitimate domain sentinel, not an error (`ADR-0000`, rule 9), and the payload estimator is never invoked. |
| High-water mark | `max_session_tokens` / `max_session_index`: the single largest session's total and its index. |
| Circuit breaker | A hard, built-in cap enforced independently of the context-window math above, in both live and simulate mode: source-file size, total chunk count, loop-item count. |

## 4. Behaviour

### 4.1 Applicability gate

`ContextWindowEstimator.run` only estimates when `chars_per_token_float_setting`,
`max_context_token_int_setting` and `max_output_tokens_int_setting` are all set.
Otherwise it returns a report with `is_valid=None`, `max_tokens_limit=None`,
`max_session_tokens=None`, `max_session_index=-1`, `total_tokens=0`, without calling the
injected `PayloadEstimator` at all.

### 4.2 Per-session estimate

For each chat session (in order), the estimator asks the injected `PayloadEstimator` for
the input token count, adds the reserved output tokens
(`max_output_tokens_int_setting.value`), and:

- accumulates the sum into `total_tokens`;
- records the session's own input and total counts;
- updates the high-water mark when this session's total exceeds the current maximum.

### 4.3 Enforcement

When a session's total exceeds `max_context_tokens`:

- outside simulate mode: `ContextWindowEstimator.run` raises immediately, naming the
  failing session index — no request for any session is sent.
- inside simulate mode: no exception; the report's `is_valid` becomes `False` and a
  human-readable warning naming both numbers is appended, so a later worker (`SIMU`,
  `OUTP`) can display it.

An unexpected failure from the injected `PayloadEstimator` is wrapped as
`ContextWindowValidatorError`, with the original message preserved.

### 4.4 Circuit breakers

Independent of the token math above, enforced identically in live and simulate mode:

| Breaker | Limit | Enforced by |
|---|---|---|
| Source-file size | 100 MB per file (`SimpleTextFileReader.MAX_FILE_SIZE_BYTES`) | `SimpleTextFileReader.read` |
| Total chunk count | 200 by default (`MaterialTokenizer.MAX_TOTAL_CHUNKS`), overridable downward via `--max-chunks` | `MaterialTokenizer.run`, across all resource sections combined |
| Loop-item count | 50 (`LoopBuilder.MAX_LOOP_ITEMS`) | `LoopBuilder.run`, for both plain-text and JSONL loop files; blank/whitespace-only lines are excluded from the count before it is checked |

`MaterialTokenizer` additionally emits non-aborting, `INFO`-level diagnostic notes: one
for a final chunk shorter than its own threshold, a distinct one for a chunk exceeding a
configured `pack_limit_chars`, and none for a normally sized chunk.

## 5. Error cases

- Context window exceeded, live mode: `ContextWindowValidatorError`, run aborts before
  any request is sent.
- Context window exceeded, simulate mode: no abort; recorded as a warning and
  `is_valid=False` on the report.
- Source file over 100 MB: abort naming the file and suggesting the file be split, at
  read time, before tokenizing.
- More than the effective chunk limit (200, or the `--max-chunks` value) across all
  resource sections combined: abort naming the limit and suggesting a narrower regex or
  fewer files.
- More than 50 real loop items (blank lines excluded), plain text or JSONL: abort
  naming the limit and suggesting the loop be split or batched.
- Any other unexpected estimator failure: wrapped as `ContextWindowValidatorError`,
  cause preserved.

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`LIMT-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

### Context window estimation

- **LIMT-01** Given `chars_per_token`, `max_context_tokens` and `max_output_tokens` are
  not all set, when `ContextWindowEstimator.run` is called, then it returns a report
  with `is_valid=None`, `max_tokens_limit=None`, `max_session_tokens=None`,
  `max_session_index=-1`, `total_tokens=0`, and the payload estimator is never invoked.
- **LIMT-02** Given all three settings are set and every session's total is under the
  limit, when `run` is called, then `is_valid=True`, `max_tokens_limit` reflects the
  setting, `total_tokens` is the sum of input-plus-reserved-output across sessions, and
  no warnings are recorded.
- **LIMT-03** Given verbose logging is enabled and the payload is within limit, when
  `run` is called, then it completes normally and returns `is_valid=True` (regression
  guard against a past `NameError` in the verbose-only log branch).
- **LIMT-04** Given a session's total exceeds `max_context_tokens` and simulate mode is
  off, when `run` is called, then it raises `ContextWindowValidatorError` naming the
  failing session index, with no leaked internal error text.
- **LIMT-05** Given the same over-limit condition with simulate mode on, when `run` is
  called, then no exception is raised; the report has `is_valid=False` and exactly one
  warning naming both the estimated and limit token counts.
- **LIMT-06** Given several sessions of differing size, when `run` is called, then
  `total_tokens`, the per-session token counts, and the high-water mark
  (`max_session_tokens`/`max_session_index`) are computed correctly across all of them.
- **LIMT-07** Given the injected `PayloadEstimator` raises an unexpected error, when
  `run` is called, then it is re-raised as `ContextWindowValidatorError` with the
  original message preserved.

### Circuit breakers

- **LIMT-08** Given a source file at or under 100 MB, when it is read, then it is
  accepted; given a file over 100 MB, when it is read, then it aborts with a message
  naming the file and suggesting the file be split.
- **LIMT-09** Given resource sections that together produce exactly 200 chunks, when
  material is tokenized, then it succeeds; given 201 or more, even split across
  multiple sections, when tokenized, then it aborts naming the 200-chunk limit and
  suggesting a narrower regex or fewer files.
- **LIMT-10** Given `--max-chunks` set below the default, when material is tokenized,
  then that lower value is enforced instead of 200, with the configured number named in
  the abort message.
- **LIMT-11** Given a final chunk shorter than the tokenizer's own threshold, when
  tokenizing completes, then an `INFO` note is emitted; given one exceeding a
  configured `pack_limit_chars`, then a distinct `INFO` note is emitted; given a
  normally sized chunk, then neither note appears.
- **LIMT-12** Given a loop file, plain text or JSONL, with at most 50 real entries
  (blank/whitespace-only lines excluded from the count), when it is built, then it
  succeeds with exactly that many lines; given 51 or more, when built, then it aborts
  naming the 50-item limit and suggesting the loop be split or batched.

## 7. Open questions

- None yet.

## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.2 (2026-09-25): initial version, derived from `context_window_estimator.py`,
  `simple_text_file_reader.py`, `material_tokenizer.py`, `loop_builder.py` and their
  tests.
