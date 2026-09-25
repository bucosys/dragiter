# Execution against an LLM — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-exec-execution.md` |
| Code | `EXEC` |
| Type | functional |
| Version | 0.3 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | `LIMT`, `OUTP`, `CONF` |

## 1. Purpose

Sending requests to local or cloud providers, sequentially or batched, with retries on
failure and streaming.

## 2. Scope

In scope:

- Building chat sessions from prompt, material and loop data, and which chunks feed
  them (`MessageBuilder`).
- Choosing sequential vs. batched processing for one run.
- Choosing the live LLM adapter or the mock adapter per run (`ChatManager`), and the
  live vs. silent progress board.
- Streaming a completion from an OpenAI-compatible endpoint and assembling it into one
  result (`OpenAIServiceExt`).
- Retrying a failed request and deciding which faults are worth retrying
  (`CompletionRetryPolicy`).
- TLS and mutual TLS transport configuration for the request (`OpenAITransportFactory`).
- Wrapping failures from a single session dispatch into a run-level error.

Out of scope: Limits checked before sending (see `LIMT`); writing results (see `OUTP`);
what the mock adapter simulates and how a simulate run is reported (see `SIMU`);
settings precedence and provider switching (see `CONF`).

## 3. Terms

| Term | Meaning |
|---|---|
| Chat session | One request unit: system instruction, first message, material message(s) and synthesis, built by `MessageBuilder` for one chunk (sequential) or all valid chunks (batched). |
| Valid chunk | A `Chunk` with `valid=True`. Only valid chunks reach a session; see 4.1. |
| Sequential processing | `prompt.sequential_processing=True`: one session per (valid chunk × loop line), never combining chunks. |
| Batched processing | `prompt.sequential_processing=False`: one session per loop line, carrying every valid chunk together. |
| Streaming | `OpenAIServiceExt` always requests `stream=True` with usage included; content is assembled from delta chunks as they arrive. |
| Attempt | One request to the provider within a single `process_query` call. Attempts are 1-based. |
| Retryable fault | A fault where `CompletionRetryPolicy.is_retryable` returns `True` (4.4). |
| Terminal fault | A fault that is never retried, regardless of attempts remaining (4.4). |
| Progress listener | `StreamProgressListener`: `on_stream_chunk()` per streamed chunk, `abandon_session()` before a retry/backoff log line commits the live request line. |

## 4. Behaviour

### 4.1 Building chat sessions

`MessageBuilder.run` pre-filters `material.chunks` to those with `valid=True` before
building any session:

- Sequential mode: one session per valid chunk (× loop line, or one per chunk if the
  loop is empty). An invalid chunk produces no session at all — not an empty one.
- Batched mode: one session per loop line (or one if the loop is empty), whose material
  message(s) are built only from valid chunks. If no chunk is valid, the unresolved
  `prompt.material` template text is used as a fallback message instead of any chunk
  content — existing, intentional legacy behaviour, not an error.

### 4.2 Provider and board selection

`ChatManager.run` selects, once per run and without reassigning any collaborator
afterwards (`ADR-0000`, rule 6):

- the mock adapter instead of the live one when `ep.simulate_bool_setting` is set (what
  the mock returns is `SIMU`'s concern);
- the verbose progress board instead of the silent one when `lp.verbose_bool_setting`
  is set.

Sessions are dispatched one at a time, in order. Each session is persisted immediately
after its result returns (`sink.persist`, see `STAG`), before the next session starts.

### 4.3 Streaming a completion

`OpenAIServiceExt._consume_stream` iterates the provider's stream: each content delta is
appended, `finish_reason` is taken from whichever chunk carries one (defaulting to
`"stop"` if none does), and token usage is read from any chunk carrying a `.usage`
payload, from either a `prompt_tokens`/`completion_tokens` or an `input_tokens`/
`output_tokens` field.

### 4.4 Retry policy

`CompletionRetryPolicy` governs one `process_query` call:

- `max_attempts(aisp)` is `aisp.max_retries_int_setting.value` when set, otherwise `1`
  (no retry).
- `wait_seconds(attempt, retry_delay)` is `0` for attempt 1 and
  `retry_delay * 2 ** (attempt - 2)` for later attempts (exponential backoff).
- Retryable: `RateLimitError`, `APIConnectionError`, and any HTTP 5xx status in the
  range 500–599 except 504.
- Terminal (never retried): HTTP 504, a gateway/stream-timeout message, `APITimeoutError`,
  a message matching "the model runner has unexpectedly stopped" (Ollama crash), and any
  non-5xx client error.
- Before a retried attempt, the progress listener's `abandon_session()` is called first,
  so the live request line is committed before the warning is logged.

### 4.5 Client initialisation and transport

`OpenAITransportFactory.create` builds the HTTP transport from `aisp`: a custom CA
bundle (`ca_bundle_file`) sets `verify`; a client certificate alone (`client_cert_file`)
is passed as `cert`; a client certificate plus a separate key
(`client_cert_file` + `client_key_file`) builds an `ssl.SSLContext` via
`load_cert_chain` for mutual TLS. TCP keepalive is enabled when
`tcp_keep_alive_bool_setting` is set. A failure while building the transport or the SDK
client is wrapped as an initialisation failure, distinct from a mid-stream failure.

## 5. Error cases

- Any exception from `llm_service.process_query` (including a terminal or
  retry-exhausted fault) aborts the whole run: `ChatManager.run` does not return partial
  `ChatResults` for the sessions already dispatched — their results were, however,
  already persisted to the run workspace before the failure (`STAG`).
- Client/transport construction failure (bad CA bundle, bad cert/key, or any other
  exception raised while creating the client) is reported as
  `"Failed to initialise OpenAI client (check CA-bundle / client cert / key)."`, so it is
  never confused with a fault that happened after the connection was established.
  An unexpected exception raised later, while consuming the stream, is wrapped as an
  `OpenAIServiceError` without that initialisation wording.
- A gateway timeout (HTTP 504, or a message naming a gateway/stream timeout) fails
  immediately after the first attempt that hits it, never retried, with a message
  explaining that retrying the same prompt will not help.
- Exhausting `max_attempts` on a retryable fault fails with a message naming the
  attempt count (`"Attempt N/N failed: …"`).
- `ChatSessionsValidator` rejects a `None` `ChatSessions` object or one whose
  `session_list` is `None` before `ChatManager` ever runs (`ADR-0000`, rule 3).

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`EXEC-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

### Session construction

- **EXEC-01** Given a sequential prompt and material with a mix of valid and invalid
  chunks, when `MessageBuilder` builds chat sessions, then exactly one session is
  created per valid chunk and no session is created for an invalid one.
- **EXEC-02** Given a sequential prompt and material where every chunk is invalid, when
  sessions are built, then no `ChatSession` is created at all.
- **EXEC-03** Given a sequential prompt and material where every chunk is valid, when
  sessions are built, then one session is created per chunk.
- **EXEC-04** Given a batched prompt and material with a mix of valid and invalid
  chunks, when a session is built, then only the valid chunks' content appears among
  the material messages.
- **EXEC-05** Given a batched prompt and material where every chunk is invalid, when a
  session is built, then the material placeholder template is left unresolved rather
  than any invalid chunk's content appearing.

### Retry policy

- **EXEC-06** Given `max_retries` is not set, when `max_attempts` is asked, then it
  returns `1`.
- **EXEC-07** Given `max_retries=N`, when `max_attempts` is asked, then it returns `N`.
- **EXEC-08** Given attempt 1, when `wait_seconds` is computed, then it is `0`; given a
  later attempt, then it is `retry_delay * 2 ** (attempt - 2)`.
- **EXEC-09** Given an HTTP 500/502/503 status error, a connection error, or a 429 rate
  limit, when classified, then `is_retryable` is `True`.
- **EXEC-10** Given an HTTP 504, a gateway/stream-timeout message, an `APITimeoutError`,
  an Ollama runner-crash message, or a non-5xx client error, when classified, then
  `is_retryable` is `False`.
- **EXEC-11** Given a transient 503 on the first attempts and success within
  `max_attempts`, when `process_query` runs, then it retries and returns the successful
  result.
- **EXEC-12** Given a 504 gateway timeout, when `process_query` runs, then it fails
  after the first attempt with no retry, message naming the timeout.
- **EXEC-13** Given repeated 500s exhausting `max_attempts`, when `process_query` runs,
  then it fails naming the attempt count (`"Attempt N/N"`).

### Client initialisation and transport

- **EXEC-14** Given the transport factory raises while constructing the client (e.g. a
  bad CA bundle), when `process_query` runs, then the failure is labelled as an
  initialisation failure.
- **EXEC-15** Given an unexpected exception while consuming the stream, when
  `process_query` runs, then it is wrapped as `OpenAIServiceError` without being
  labelled as an initialisation failure.
- **EXEC-16** Given a custom CA bundle configured, when a live request is sent over TLS
  to an endpoint presenting a certificate from that bundle, then the connection
  succeeds. Verified against a local Caddy proxy; skipped when that proxy or the
  configured CA/Ollama backend is unavailable.
- **EXEC-17** Given a client certificate and key configured, when a live request is
  sent to an endpoint requiring mutual TLS, then the connection succeeds. Verified
  against a local Caddy proxy; skipped when that proxy or the configured
  cert/key/Ollama backend is unavailable.

## 7. Open questions

- `ChatManager`'s own dispatch behaviour (provider/board selection, per-session persist
  ordering, wrapping a `PersistenceError` distinctly, calling `abandon_session()` on any
  exception) is exercised in `tests/test_staging_workspace.py` and
  `tests/test_session_board_and_persistence.py`, which belong to the `OUTP`/`SIMU`
  initial-draft pass. Once those specs are drafted, criteria for that behaviour should
  be added here (or cross-referenced) with those files as their test evidence.
- The streaming heartbeat (`OpenAIServiceExt._log_progress`, one glyph at most every ten
  seconds when verbose and no progress listener is supplied) has no dedicated test yet.
## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.2 (2026-09-25): initial version, derived from `message_builder.py`, `chat_manager.py`,
  `openai_service_ext.py`, `openai_runtime.py` and their tests.
- 0.3 (2026-09-26): removed the open question about `infrastructure/llm/openai_service.py`
  (`OpenAIService`) — confirmed dead (no imports, no inheritance, not wired into `cli.py`)
  and deleted, along with the `httpx` runtime dependency it alone needed.
