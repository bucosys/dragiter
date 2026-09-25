# Simulation mode — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-simu-simulation.md` |
| Code | `SIMU` |
| Type | functional |
| Version | 0.4 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | `EXEC`, `LIMT`, `OUTP` |

## 1. Purpose

Running a job completely without calling the LLM and showing what would be sent —
never what a model would reply. Simulation is a preview of requests, chunk selection
and context-window arithmetic, not a fake conversation.

## 2. Scope

In scope:

- The `-s` / `simulate_bool_setting` flag and its effect on which service `ChatManager`
  calls for every session.
- `MockAIService`'s behaviour: what it returns, and that it never performs network I/O
  or streaming.
- That a simulate run's artefacts show the outgoing request (role/content), aggregate
  facts (chunks, sessions, pack, window, warnings) and never a synthesised reply.
- That a simulate run remains fully auditable (activity log) like a live run.
- That a simulate run's workspace is **committed** exactly like a live run's —
  there is no discard path anymore (see `STAG`, technical, and `OUTP` for what
  "committed" means).

Out of scope: Where the boards are written to (stdout vs. file, see `OUTP`); how
context-window validity is computed (see `LIMT`); retries and streaming for live calls
(see `EXEC`).

## 3. Terms

| Term | Meaning |
|---|---|
| Simulate mode | Run with `-s` set, or any result whose `finish_reason` is `"mock"`. |
| Mock service | `MockAIService`, the `LLMService` implementation used instead of the real provider in simulate mode. |
| Run board | Aggregate, run-level facts (`SimulationBrief`), assembled by `ChatManager` once per run and persisted as a leading shard for `-o`/stdout (never for `-O`). |
| Session board | Per-session facts (chunk, loop entry, tokens, pack) (`SimulationSessionBrief`), assembled by `ChatManager` and persisted as part of that session's shard. |
| Payload table | The role/content table of the messages that would have been sent for one session — the request, never a reply. Appended after the session board in the same shard. |

## 4. Behaviour

### 4.1 Selecting the mock service

`ChatManager.run` reads `ep.simulate_bool_setting.value` once per run and uses
`self._mock_service` instead of `self._llm_service` for every session when it is true
(`application/pipeline/chat_manager.py`). The live service is never constructed calls
to it in this branch — there is no partial live/mock mix within one run driven by this
flag (SIMU-01).

### 4.2 What the mock service returns

`MockAIService.process_query` (`infrastructure/llm/mockai_service.py`) requires a
non-empty `input_chat_message_list` (else `MockAIServiceError`, SIMU-06) and
returns a `ChatResult` with `output_chat_message.content` set to the **empty
string** and `finish_reason` set to `"mock"`. No network call is made; nothing is
streamed to a progress listener. The mock service's own returned content is never
user-facing — `ChatManager` overwrites it before persisting (§4.3).

### 4.3 What appears in the output

`ChatManager` (`application/pipeline/chat_manager.py`), not `OutputWriter`, decides
what a simulate session's content is, and persists it as an ordinary shard through
the same `PersistenceService`/`OutputCommitService` path a live reply uses (`STAG`):

- For every session, the shard content is that session's board (chunk, section,
  loop entry, token estimate and pack facts) followed by its complete outgoing
  request (role/content payload table) — never the mock reply's own content
  (SIMU-02).
- For `-o` and stdout-only (never for `-O`, which requires exactly one shard per
  session, `STAG` Section 7), `ChatManager` additionally persists one leading
  shard with the aggregate run-level board (model, sessions, chunks / valid
  chunks / source files, loop items, total characters, pack limit and its
  origin, small/oversize chunk counts, window validity, peak/limit tokens, the
  session at which the peak occurred, warning count, output target).
- `OutputWriter` then commits exactly like it would for a live run — it does not
  know or care that the run was simulated.

Two consequences of sharing the live commit path, both deliberate:

- **stdout-only now shows full detail.** Previously only the aggregate board was
  printed; now stdout gets everything `-o` already got — the aggregate board
  followed by every session's board and complete request (SIMU-07) — because
  stdout-only's commit is Assembly-then-print, the same as `-o`'s.
- **The join character between shards is `output_delimiter`, not a hardcoded
  `***`.** `-o`/stdout-only used to wrap the whole file in `***` thematic breaks
  in one pass; now each shard is joined to the next with the run's actual
  `output_delimiter` (`STAG`'s Assembly). Within one shard, the board and the
  request are still joined by `***` as before — only the *inter*-shard join
  character changed.

### 4.4 Context-window facts on the board

When the context estimator reports "not applicable" (`ContextValidationReport.is_valid
is None`, see `spec-limt-limits.md` for when and why), both the live start board and
the simulate run board render `window n/a` and `peak -- / --` rather than `yes` and
`0 / 0` (SIMU-03).

### 4.5 Audit and disposal

A simulate run still writes activity records like a live run (see `spec-audt-audit.md`)
(SIMU-04). Its workspace is **committed** exactly like a live run's —
`OutputCommitService.commit`, not `discard` (SIMU-08; `STAG`, technical).

## 5. Error cases

- No input messages on a session handed to the mock service: `MockAIServiceError`
  (SIMU-06).
- All other error handling for a simulate run (workspace creation, discard) is `STAG`'s.

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`SIMU-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

- **SIMU-01** Given `-s` is set, when any session is processed, then the mock service
  handles it and the live LLM service is never invoked, for every session of the run.
- **SIMU-02** Given a simulate run with `-o` or `-O`, when its output is written, then
  each session's payload table shows the outgoing request messages and no assistant/reply
  row ever appears.
- **SIMU-03** Given the context estimator reports "not applicable", when a live start
  board or a simulate run board is rendered, then it shows `window n/a` and
  `peak -- / --` instead of `yes` and `0 / 0`.
- **SIMU-04** Given `-s` and activity logging enabled (`-a FILE`), when the run
  completes, then the activity file contains multiple well-formed JSON records
  describing the run.
- **SIMU-05** Given `MockAIService` processes a session, when it is asked to stream,
  then no stream-chunk callback is ever invoked.
- **SIMU-06** Given a chat session with no input messages, when the mock
  service processes it, then it raises `MockAIServiceError` instead of returning an
  empty reply.
- **SIMU-07** Given stdout-only and a simulate run, when the run completes, then
  stdout shows the aggregate run board followed by every session's board and
  complete request — not just the aggregate board.
- **SIMU-08** Given a simulate run, when it completes, then its workspace is
  committed exactly like a live run's, never discarded.
- **SIMU-09** Given a `ResultBoardService` implementation other than
  `MarkdownResultBoard` is injected into `ChatManager`, when a simulate run
  completes, then the injected implementation's output appears instead of the
  default Markdown board.

## 7. Open questions

- Whether `estimated_input_tokens` being silently `None` (no payload estimator, or
  `chars_per_token` unset) should be surfaced to the user as a warning rather than a
  quiet omission from the mock payload.

## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.2 (2026-09-25): initial version. Purpose, scope, terms, behaviour, error cases and
  acceptance criteria SIMU-01 to SIMU-06 added, derived from
  `application/pipeline/chat_manager.py`, `infrastructure/llm/mockai_service.py` and
  `application/pipeline/output_writer.py`.
- 0.3 (2026-09-25): SIMU-06 covered by new `tests/test_mockai_service.py`; *proposed*
  mark dropped.
- 0.4 (2026-09-25): rewritten for the live/simulate unification —
  `MockAIService` no longer returns a JSON blob, `ChatManager` builds and
  persists the session's board and request itself, and the workspace is
  committed rather than discarded. New SIMU-07 (stdout now shows full detail),
  SIMU-08 (commit, not discard) and SIMU-09 (result-board injection moved here
  from `OUTP-13`, now withdrawn).
