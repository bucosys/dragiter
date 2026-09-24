# Simulation mode — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-simu-simulation.md` |
| Code | `SIMU` |
| Type | functional |
| Version | 0.2 |
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
- That a simulate run's workspace is discarded, never committed to a sink (see `STAG`,
  technical, and `OUTP` for what "committed" means).

Out of scope: Where the boards are written to (stdout vs. file, see `OUTP`); how
context-window validity is computed (see `LIMT`); retries and streaming for live calls
(see `EXEC`).

## 3. Terms

| Term | Meaning |
|---|---|
| Simulate mode | Run with `-s` set, or any result whose `finish_reason` is `"mock"`. |
| Mock service | `MockAIService`, the `LLMService` implementation used instead of the real provider in simulate mode. |
| Run board | Aggregate, run-level facts rendered once per run (`SimulationBrief`). |
| Session board | Per-session facts (chunk, loop entry, tokens, pack) rendered once per session (`SimulationSessionBrief`). |
| Payload table | The role/content table of the messages that would have been sent for one session — the request, never a reply. |

## 4. Behaviour

### 4.1 Selecting the mock service

`ChatManager.run` reads `ep.simulate_bool_setting.value` once per run and uses
`self._mock_service` instead of `self._llm_service` for every session when it is true
(`application/pipeline/chat_manager.py`). The live service is never constructed calls
to it in this branch — there is no partial live/mock mix within one run driven by this
flag (SIMU-01).

### 4.2 What the mock service returns

`MockAIService.process_query` (`infrastructure/llm/mockai_service.py`) requires a
non-empty `input_chat_message_list` (else `MockAIServiceError`, SIMU-06 *proposed*) and
returns a `ChatResult` whose `output_chat_message.content` is a JSON object describing
the request it received — `model`, `input_message_count`, an optional
`estimated_input_tokens` (only when a payload estimator and `chars_per_token` are both
set), the last message's role and a 300-character preview, and the full last-message
content — with `finish_reason` set to `"mock"`. No network call is made; nothing is
streamed to a progress listener.

### 4.3 What appears in the output

`OutputWriter` treats a run as a simulation when either `ep.simulate_bool_setting` is
true or any result's `finish_reason == "mock"` (`OutputWriter._is_simulation`). In that
case it renders boards instead of committing real content:

- One run board per run, with aggregate facts (model, sessions, chunks / valid chunks /
  source files, loop items, total characters, pack limit and its origin, small/oversize
  chunk counts, window validity, peak/limit tokens, the session at which the peak
  occurred, warning count, output target).
- One session board per session, with that session's chunk, section, loop entry, token
  estimate and pack facts.
- For `-o`/`-O`, one payload table per session, showing the exact outgoing messages
  (role and content) — never the mock reply's content itself (SIMU-02).

### 4.4 Context-window facts on the board

When the context estimator reports "not applicable" (`ContextValidationReport.is_valid
is None`, see `spec-limt-limits.md` for when and why), both the live start board and
the simulate run board render `window n/a` and `peak -- / --` rather than `yes` and
`0 / 0` (SIMU-03).

### 4.5 Audit and disposal

A simulate run still writes activity records like a live run (see `spec-audt-audit.md`)
(SIMU-04). Its workspace is discarded rather than committed — `OutputCommitService.discard`,
not `commit` (`STAG`, technical).

## 5. Error cases

- No input messages on a session handed to the mock service: `MockAIServiceError`
  (SIMU-06 *proposed* — implemented, not yet covered by an owned test).
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
- **SIMU-06** *proposed* Given a chat session with no input messages, when the mock
  service processes it, then it raises `MockAIServiceError` instead of returning an
  empty reply.

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
