# dragiter Requirements Profile

**Document type:** product and system requirements  
**Subject:** dragiter (Deterministic Context Iterator)  
**Licence:** AGPL-3.0-or-later  
**Language:** British English  
**Audience:** operators, integrators, reviewers

This profile states the product as implemented. Example 04 splits it with
`regex_patterns`: pattern 0 cuts on `## ` chapter headings; pattern 1 cuts
oversized pieces on `### ` when `pack_limit_chars` is in force. `####`
requirement blocks stay inside the parent piece.

---

## 1. Purpose, identity and product boundary

### 1.1 Why the product exists

Operators need to walk a large text corpus through an OpenAI-compatible
model in bounded pieces, with deterministic chunking, an inspectable dry
run, and Unix-friendly file and stream routing.

### 1.2 Product identity

dragiter is a command-line pipeline, not a chat application. One process
loads settings, collects files, splits them, builds sessions, optionally
calls a model, and writes results. There is no hidden conversational
memory between runs.

### 1.3 In scope

CLI and TOML configuration; resource collection; staged regex chunking;
optional `chunk_substitutions`; include/exclude validity flags; packing
inside one file; prompt templates and loops; simulate and live modes;
context-window estimates; output files and directories; activity traces;
OpenAI-compatible streaming with retries and optional mTLS.

### 1.4 Out of scope

A hosted multi-user service, a GUI, fine-tuning, embedding indexes, and
any second rewrite pass disguised as a validity filter.

#### REQ-ID-001 — Command-line product

The supported interface is the `dragiter` command, its flags, environment
variables, and TOML files.

#### REQ-ID-002 — No hidden conversational state

A run must not read or write an implicit chat history. Only files, stdin
and flags supplied for that process count.

---

## 2. Stakeholders and jobs

### 2.1 Primary stakeholders

The operator who runs the CLI; the integrator who embeds it in a pipeline;
the reviewer who reads simulate boards and activity JSONL.

### 2.2 Jobs to be done

Dry-run a corpus; send bounded chunks to a local or remote model; keep
partial results if a later call fails; audit what was sent.

#### REQ-STK-001 — Operator can dry-run

`-s` / `--simulate` must assemble sessions and write boards without calling
the model.

#### REQ-STK-002 — Integrator can pipe stdin

Standard input is available as `{STDIN}` or with `-t`. Result text follows
the `-o` / `-O` sink rules.

---

## 3. Architecture and run lifecycle

### 3.1 Pipeline

Workers run in a fixed order: configuration, resources, tokenisation,
loop, prompt, sessions, context estimate, chat, output. Dependencies are
injected by type.

### 3.2 Precedence

CLI beats configuration file beats environment beats defaults. A higher
origin cannot be overwritten by a lower one.

### 3.3 Exit status

`0` success; `1` failure; `130` interrupt. Exclusive output mode leaves
already-written files in place on interrupt.

#### REQ-SYS-001 — Settings precedence is total

Every settable value records an origin. Conflicts resolve by the order
above, never by last-write-wins across sources.

#### REQ-SYS-002 — Base directory is explicit

`-b` is not pre-filled with the current working directory. Relative paths
rebase onto `-b` only when `-b` is set.

---

## 4. Material intake

### 4.1 Resource file

Each TOML table is a section: `glob_patterns`, optional `base_directory`,
`regex_patterns` (list), optional filters, `pack_limit_chars`, optional
`chunk_substitutions`.

### 4.2 Discovery

Relative globs stay under the section root. Absolute globs are an explicit
escape. Empty or binary files are rejected.

#### REQ-RES-001 — Singular regex key is a hard error

`regex_pattern` aborts collection and names the section. Use
`regex_patterns`.

#### REQ-RES-002 — Relative globs cannot escape their root

A match outside the resolved section root is dropped.

#### REQ-RES-003 — Sections stay independent

Files, patterns, filters, pack budget and substitutions do not leak
across section tables.

---

## 5. Chunking, substitutions and packing

### 5.1 Staged split

The first pattern always cuts the raw file at match starts. Later
patterns run only on pieces that still exceed the effective pack budget.
Capturing groups do not change cut points.

### 5.2 Substitutions

`chunk_substitutions` is an ordered list of `{ pattern, replacement }`
tables. Rules run after the split and before filters and packing.
Replacements are literal. Empty replacement deletes. Whitespace-only
pieces after substitution are discarded.

### 5.3 Filters and packing

Include/exclude set `valid`; they do not rewrite text. Packing joins
consecutive same-file, same-validity pieces up to the character budget.
Valid and invalid pieces are never mixed. A global pack value, including
`0`, overrides the section key.

### 5.4 Cap

More than 200 chunks aborts unless `--max-chunks` raises the cap
(minimum 1).

#### REQ-CHK-001 — First pattern always cuts

Pattern 0 applies to the raw file even when packing is off.

#### REQ-CHK-002 — Later patterns are overflow only

Pattern 1+ runs only while a piece exceeds the effective budget.

#### REQ-CHK-003 — Packing stays inside one file

Pieces from different files are never joined.

#### REQ-CHK-004 — Circuit breaker at 200 chunks

The default cap is 200. Operators raise it explicitly.

---

## 6. Prompts and sessions

### 6.1 Templates

Prompt files are TOML: system instruction, task parts, behaviour,
outcome. Placeholders include `{CHUNK_CONTENT}`, `{CHUNK_FILE_NAME}`,
`{CHUNK_NUM_ID}`, `{LOOP_CONTENT}`, `{STDIN}` and JSONL keys.

### 6.2 Sequential versus batched

`sequential_processing` builds one session per valid chunk (and loop
row). Batched mode packs valid material into fewer sessions.

#### REQ-PMT-001 — Templates are files

`-p` loads a TOML template. `-t` supplies a task string instead of a
file, not a second hidden template language.

---

## 7. Loops

### 7.1 Sources

A loop file is plain text (one item per line) or JSONL (object keys
become placeholders). No loop file means one pass over the material.

#### REQ-LOP-001 — JSONL keys become placeholders

Each key in a JSONL object is available in the template for that row.

---

## 8. Simulate and live

### 8.1 Simulate

`-s` uses the mock adapter. No network completion. Simulate boards
describe sessions, chunks, pack origin and window facts.

### 8.2 Live

The default adapter streams via `httpx2`. SDK retries are off; dragiter
owns the retry policy. Transient 5xx and connection drops retry; 504 and
similar gateway failures are terminal.

#### REQ-EXE-001 — Simulate never calls the model

A simulate run must not perform a live chat-completions request.

#### REQ-EXE-002 — Result sink is not the verbose board

Live `-v` progress writes to stderr. Result text follows `-o` / `-O`.
Stdout receives results only when neither sink is set.

---

## 9. Context-window estimation

### 9.1 Inputs

`chars_per_token`, `max_context_tokens` and `max_output_tokens`. If those
are unset, the estimate is not applicable.

### 9.2 Honesty

The estimate is a character heuristic, not a tokenizer. Boards must not
present it as a provider-exact count.

#### REQ-CTX-001 — Window facts stay consistent

When the inputs are set, peak, limit and pass/fail on the board refer to
the same formula.

---

## 10. Output routing

### 10.1 Destinations

`-o` one file; `-O` one file per session; otherwise stdout. File routing
replaces the stdout echo.

### 10.2 Modes

Default open mode is exclusive create (`x`). `w` overwrites; `a` appends.
Directory writes stage then rename.

#### REQ-OUT-001 — Exclusive create is the default

An existing target in mode `x` fails the run.

#### REQ-OUT-002 — Partial live results are kept

Each successful live completion is also written under
`.dragiter-partial/` so a later failure does not discard earlier replies.

---

## 11. Configuration surface

### 11.1 Origins

CLI flags, config TOML, `DRAGITER_*` environment variables, defaults.

### 11.2 Flags that matter here

`-p`, `-r`, `-l`, `-t`, `-s`, `-v`, `-d`, `-o`, `-O`, `-m`, `-b`, `-c`,
`--pack-limit-chars`, `--max-chunks`.

---

## 12. Providers, transport and TLS

### 12.1 Client

Live completions use an OpenAI-compatible Chat Completions URL. Optional
`--ca-bundle-file`, client certificate and key, `--tcp-keep-alive`.

#### REQ-NET-001 — Adapter owns retries

`max_retries=0` on the SDK. Attempt count is `max_retry` on dragiter.

---

## 13. Observability

### 13.1 Debug versus verbose

`-d` is the logger (DEBUG). `-v` is the stderr run board (start block,
one request line per completion, closing block). Combined, the board is
mixed into the debug stream. `-v` alone does not raise the root logger
to INFO.

### 13.2 Activity

`--activity-file` appends JSONL. Secrets in settings are masked.

#### REQ-OBS-001 — Boards do not write into result files

The verbose board and simulate stdout brief stay off the `-o` / `-O`
payload.

---

## 14. Security

### 14.1 Defaults

No implicit world-readable secrets. API keys come from settings, not from
argv echo. Generated names are sanitised. Resource globs cannot traverse
a relative root.

#### REQ-SEC-001 — Activity traces mask secrets

Values marked secret must not appear in clear in activity JSONL.

---

## 15. Operator experience

### 15.1 Help

No arguments prints a banner and short usage. `--info` prints the
operator page. `--help` is argparse.

### 15.2 Interrupt

Ctrl-C prints a short note on stderr and exits 130.

---

## 16. Quality attributes

Deterministic chunking for the same files and patterns; fail-fast on
illegal resource keys; bounded work via `max_chunks`; inspectable
simulate path before spend.

---

## 17. Acceptance for this example

### 17.1 Split

From `examples/04_staged_regex_sample`, a simulate run with
`--pack-limit-chars 0` yields one piece per `##` chapter that has body
text. With the section budget, oversized chapters may refine on `###`
and neighbours may pack.

### 17.2 Resource file

`04_resource_staged_regex.toml` must keep `regex_patterns` as a list and
must not contain `regex_pattern`.

#### REQ-EX-001 — Working directory matters

The resource glob is the profile file name. Run from this example
directory or pass `-b` so the file is found.

---

## 18. Non-goals

No second product UI. No silent upgrade of `regex_pattern`. No packing
across files. No treating filters as a rewrite engine.

---

## 19. Glossary

**Chunk** — material unit after split, substitution, filter and optional
pack.  
**Piece** — text span after a regex cut, before packing.  
**Section** — one table in the resource TOML.  
**Board** — compact stderr or simulate summary, not the model reply.  
**Origin** — which source set a setting.

---

## 20. Document control

This profile replaces the long working draft that existed only to force
overflow cuts. Length is no longer a requirement of the example. Edit
the text when the product contract changes; keep `##` / `###` / `####`
levels so the staged-regex demonstration still has grain.
