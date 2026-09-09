# dragiter Requirements Profile

**Document type:** product and system requirements  
**Subject:** dragiter (Deterministic Context Iterator)  
**Licence of the product:** AGPL-3.0-or-later  
**Language of this profile:** British English  
**Status:** working profile for the `04_textmeter_sample` example  
**Audience:** operators, integrators, reviewers

This profile describes the product as it exists in the dragiter source tree
and public documentation. It is written so that a later resource definition
can split the text with `regex_patterns`: the first pattern cuts on level-2
chapter headings; a second pattern refines oversized pieces on level-3
headings when a `pack_limit_chars` budget is in force.

The document is long on purpose. Several chapters exceed a typical pack
budget on their own. That is a property of the example, not padding for its
own sake. Factual claims follow the shipped behaviour: command-line
precedence, resource sections, staged regular expressions, packing inside
one file, simulation boards, activity traces, OpenAI-compatible streaming,
and the security defaults documented in the manual and technical reference.

---

## 1. Purpose, identity and product boundary

### 1.1 Why the product exists

Assembling context for a large language model by hand is slow and easy to
get wrong. dragiter replaces that ritual with a Unix-style pipeline. The
operator supplies material, a prompt template and an optional loop file.
The tool builds deterministic chat requests and writes the replies where it
is told to write them. There is no interactive chat surface, no hidden
session memory between runs, and no provider-specific workflow language.

The product name states the contract. *Deterministic* means the same files
and the same settings produce the same request payloads. *Context* means
the work is the assembly of material into model-visible messages.
*Iterator* means a loop file may drive many sessions from one invocation.

### 1.2 Product identity

dragiter is a command-line tool. It is installed with `pip install dragiter`
and requires Python 3.11 or later. Source and releases live on GitLab under
bucosys/dragiter. The public site is dragiter.app. Versioning follows
calendar versioning of the form `YYYY.M.D` with optional pre-release
suffixes such as `b1` or `rc1`.

Companion utilities exist beside the main binary:

- `dragiter-gen-docs` extracts the manual, technical reference and man-page
  summary.
- `dragiter-gen-examples` extracts the bundled sample projects.

Documentation follows the Diátaxis split. The manual holds tutorial,
how-to and explanation. The technical reference holds flags, schemas,
placeholders, defaults and activity-log record shapes. `dragiter --info`
prints the compact man-page text.

### 1.3 In scope

The following capabilities are in scope because they are implemented:

- reading text files discovered by glob patterns in a resource TOML
- splitting those files with one or more regular expressions
- packing consecutive pieces of the same file up to a character budget
- include and exclude filters that mark a chunk valid or invalid
- prompt templates in TOML with system, material and synthesis sections
- sequential or batched processing of chunks
- loop files as plain text or JSONL
- standard-input capture into the `{STDIN}` placeholder
- simulation without network calls
- live calls through an OpenAI-compatible chat-completions endpoint
- streamed completions on the live path
- context-window estimation from character counts
- output to stdout, one file (`-o`) or many files (`-O`)
- exclusive, overwrite and append open modes
- staged directory writes so a conflict does not discard generated text
- JSONL activity traces with masking of fields whose names contain `key`
- retries for transient connection loss and selected 5xx responses
- optional custom CA bundle and mutual TLS
- configuration from CLI, TOML, environment and built-in defaults

### 1.4 Out of scope

The following are not product goals and must not be implied by this profile:

- a graphical or web chat client
- a hosted multi-tenant service
- fine-tuning or model training
- embedding indexes or vector databases
- a proprietary prompt language beyond TOML templates and placeholders
- silent migration of the removed singular resource key `regex_pattern`
- automatic rewriting of the operator's source documents


#### REQ-ID-001 — Command-line product

**Statement.** dragiter shall be invoked as a command-line process and shall complete a run without requiring an interactive prompt after launch.

**Rationale.** The tool is meant to sit in scripts, Make targets and CI jobs.

**Acceptance criteria.**

1. A run started with valid flags reaches an exit status without waiting on stdin except when stdin is an intentional material source.
2. Help (`-h`), information (`--info`) and version (`--version`) flags exit after printing their text.

#### REQ-ID-002 — No hidden conversational state

**Statement.** A run shall not read or write a proprietary chat-history database. Each invocation is complete given its files and settings.

**Rationale.** Reproducibility depends on the absence of hidden memory.

**Acceptance criteria.**

1. Repeating the same command with the same files yields the same assembled request payloads in simulation mode.
2. Any persistence is limited to files the operator named (`-o`, `-O`, `-a`, `-L`).

### 1.5 Quality bar for this profile

Every requirement below is written so that an example later in
`examples/04_textmeter_sample` can count the effect of `regex_patterns`.
Chapter headings at level 2 are the coarse cut. Section headings at
level 3 are the overflow cut. Requirement blocks at level 4 stay inside
their parent section; they are not a splitting pattern in the sample
resource file.

Operators measuring the example should be able to answer, from a
simulate board and from `--verbose` notes:

- how many final chunks the document produced
- how many of those chunks are shorter than 50 characters
- how many exceed the configured pack budget
- which pattern index created or refined a piece when `--debug` is on

---

## 2. Stakeholders, jobs and operating environments

### 2.1 Primary stakeholders

The primary operator is a person who already works in a shell and who
wants language-model help over a bounded corpus: source trees, manuals,
statutes, research notes, marketing specifications. They accept that
they must write a resource file and a prompt file. They refuse to paste
the same context into a chat box twenty times.

Secondary stakeholders include reviewers who read activity logs, and
integrators who wrap dragiter in a larger pipeline (`curl | dragiter`,
or dragiter writing into a directory that another tool consumes).

### 2.2 Jobs to be done

Typical jobs that the current code already supports:

- summarise or transform every heading-sized piece of a Markdown book
- walk C source and headers with two different section definitions
- apply one prompt to many target groups listed in a JSONL loop
- dry-run a planned batch with `-s` and inspect the run board
- keep API keys out of files by using environment variables
- point the same templates at Ollama, a cloud OpenAI-compatible gateway,
  or a LiteLLM proxy by changing `base_url`, `model_name` and `api_key`

### 2.3 Operating environments

Supported environments are those where Python 3.11+ and the published
dependencies run. Live streaming requires `openai >= 3.0.0` and
`httpx2 >= 2.7.0` because the streaming path uses `DefaultHttpx2Client`.
Older OpenAI client major versions are not a supported streaming stack.

Local models via Ollama are a first-class demonstration target. Cloud
providers are reached only through OpenAI-compatible endpoints. The
product does not embed vendor SDKs beyond that protocol.


#### REQ-STK-001 — Operator can dry-run

**Statement.** An operator shall be able to inspect assembled sessions without spending tokens or opening a network connection to a model.

**Rationale.** Simulation is the documented first step in the manual.

**Acceptance criteria.**

1. `-s` / `--simulate` / `DRAGITER_SIMULATE` prevents live completions.
2. Stdout in simulate mode prints the run board rather than model prose.
3. Files written in simulate mode contain session boards and payload tables, not live model text.

#### REQ-STK-002 — Integrator can pipe stdin

**Statement.** When the prompt template contains `{STDIN}`, or when `-t` supplies a task, the process shall be able to read standard input as material.

**Rationale.** Unix composition is an explicit product claim.

**Acceptance criteria.**

1. A pipeline such as `curl -s URL | dragiter -p …` supplies the fetched text to the placeholder.
2. Absence of a `{STDIN}` placeholder does not invent a second hidden injection point.

### 2.4 What operators must bring

dragiter does not invent a corpus. The operator must point at files that
exist, encodings that the file checker accepts, and regular expressions
that compile. Invalid patterns abort with a section-qualified error.
A resource section that still uses the removed key `regex_pattern`
aborts collection. That failure is preferred to a silent whole-file
chunk.

---

## 3. System context, architecture and run lifecycle

### 3.1 Context diagram in words

Outside the process sit: the operator's files, optional environment
variables, an optional user config at `~/.config/dragiter/config.toml`,
an OpenAI-compatible HTTP endpoint, and the destinations for stdout,
output files, the activity file and the log file.

Inside the process the pipeline is staged. A resource collector resolves
globs against a section root. A tokenizer splits and optionally packs
chunks. A loop builder reads iteration lines. A message builder fills
templates. A context-window estimator may annotate token pressure. A
chat manager either mocks or streams. An output writer prints and
stores results.

### 3.2 Architectural rule of thumb

Domain models do not open sockets. File and HTTP adapters live under
infrastructure. Pipeline workers live under application. That split is
visible in the package layout (`domain`, `application/pipeline`,
`infrastructure`). This profile does not require a particular framework
beyond that layout remaining intact.

### 3.3 Run lifecycle

1. Logging is configured from `-d` / `-v` / `-L` and the matching
   environment variables before the rest of the run speaks.
2. Settings are loaded and locked by origin. A value set by the CLI
   cannot be overwritten by the config file or the environment.
3. Resources are collected. The removed singular regex key is rejected
   here, not later in the tokenizer.
4. Material is tokenised into chunks. A hard cap of 200 chunks aborts
   the run to stop combinatorial explosion.
5. The prompt template and optional loop produce chat sessions.
6. If simulation is on, or a result carries finish reason `mock`,
   output uses boards and transcripts.
7. Otherwise live streaming runs with the configured retry policy.
8. Results go to stdout and to any requested file or directory.
9. Activity records are flushed when an activity file was requested.

### 3.4 Exit status

Exit status `0` means success. Status `1` means a configuration or
critical error. Status `130` means the process was interrupted by the
operator (KeyboardInterrupt). This profile treats those three codes as
the public process contract.


#### REQ-SYS-001 — Settings precedence is total

**Statement.** Configuration values shall resolve in the order CLI, configuration file, environment, built-in default. A higher origin wins outright.

**Rationale.** The man page and manual state this order without exceptions for ordinary settings.

**Acceptance criteria.**

1. A CLI flag shadows the same key in the TOML config.
2. A config-file value shadows the environment.
3. An environment value shadows the built-in default.
4. Once set, a lower origin cannot replace the value.

**Constraints.** Boolean environment values accept TRUE/1/YES/ON/Y and FALSE/0/NO/OFF/N after strip and upper-case. Other strings raise. Native TOML booleans are required in the config file; quoted strings are not coerced there.

#### REQ-SYS-002 — Base directory is explicit

**Statement.** The global base directory shall not be pre-filled with the process current working directory. It becomes set only from `-b`, the config file or `DRAGITER_BASE_DIRECTORY`.

**Rationale.** Silent rebasing against CWD made path resolution hard to explain.

**Acceptance criteria.**

1. Unset `-b` leaves the global base-directory setting unset.
2. Resource globs without a section `base_directory` still start from CWD.
3. When `-b` is set, a relative section `base_directory` is rebased onto it; an absolute section base is not moved.

---

## 4. Material intake and resource collection

### 4.1 Resource file shape

A resource file is TOML. Each table name becomes a section name. A
section lists `glob_patterns` and may list `base_directory`,
`regex_patterns`, `include_filters`, `exclude_filters` and
`pack_limit_chars`.

`regex_patterns` is a list of strings. A single string under that same
key may be coerced to a one-element list by the domain model. The
legacy key `regex_pattern` is not accepted. If it is present on a
section, collection aborts with a message that names the section and
tells the operator to use `regex_patterns`.

When `regex_patterns` is omitted, the domain substitutes a pattern that
matches nothing. The file then becomes a single piece (after strip),
which is a defined default rather than a crash.

### 4.2 Discovery and containment

Globs are evaluated against the section search root. Relative matches
must remain inside that root after resolve. A match that escapes —
including through a symlink that points outside — is skipped and a
warning is logged. Absolute glob patterns are an explicit escape hatch:
the author wrote a fully qualified pattern, so containment against the
section root does not apply.

Only files whose encoding the file checker can detect are kept. A
failed encoding check skips the file rather than aborting the whole
section.

### 4.3 Section identity

An empty section name is rejected. Files attached to a section carry
that section name onto every chunk. Chunk identifiers are assigned per
section during tokenisation: a running `num_id` and a
`section_num_id`. Callers that format output names may use both.

### 4.4 Activity view of resources

The resources object exposes an activity dictionary with section count,
total files, and per-section fields: name, file count, the
`regex_patterns` list, filters and `pack_limit_chars`. It does not
emit a duplicate singular `regex_pattern` field.


#### REQ-RES-001 — Singular regex key is a hard error

**Statement.** If a resource section table contains the key `regex_pattern`, collection shall fail before any split is attempted.

**Rationale.** Silent omission would turn a documented heading split into one giant chunk and look like success.

**Acceptance criteria.**

1. The error text contains the section name.
2. The error text names `regex_pattern` as removed.
3. The error text names `regex_patterns` as the replacement.
4. No chunks are produced from that file for the failed run.

#### REQ-RES-002 — Globs cannot walk out of a relative root

**Statement.** A relative glob must not deliver a file whose resolved path lies outside the section root.

**Rationale.** Resource files are operator-written, but path traversal still has to be boring.

**Acceptance criteria.**

1. A pattern such as `../../secret` does not add that file when the resolved path is outside the root.
2. A warning identifies the skipped path and the root.
3. Absolute patterns remain the documented escape hatch.

#### REQ-RES-003 — Multiple sections stay independent

**Statement.** Each resource table is collected and later tokenised as its own section with its own patterns and filters.

**Rationale.** The Markdown, C and JSONL examples all rely on more than one concern being described in one file.

**Acceptance criteria.**

1. Chunks from section A do not inherit regexes from section B.
2. Activity output lists each section separately.

---

## 5. Chunking, staged regular expressions and packing

This chapter is the heart of the staged-regex example. It is intentionally
larger than a modest `pack_limit_chars`. A first pattern that cuts only
on level-2 headings will leave this chapter oversized. A second pattern
that cuts on level-3 headings should then refine it.

### 5.1 Staged split contract

Pattern 0 always runs. It cuts the file text at each match start. The
match text stays on the following piece. Capturing groups are optional
and ignored for the cut position. Consecutive identical start offsets
are skipped so a zero-width curiosity does not emit empty slices.

Later patterns run only when two conditions hold at once:

- a character budget is active (`pack_limit_chars` from the CLI or,
  failing that, from the section), and
- the piece still exceeds that budget.

If the budget is unset or `0`, overflow patterns after the first do not
run. A globally set budget, including `0`, overrides the section value.

If a later pattern produces no new cuts, the tokenizer records that the
pattern had no effect and tries the next remaining pattern. A piece
that no remaining pattern can reduce is left intact. That leftover may
then appear as an oversize final chunk.

### 5.2 Validity filters

After the text has been cut into pieces, each piece is marked valid or
invalid. Exclude filters run first and veto a piece when any of them
matches (case-insensitive, multiline). If include filters are present,
a piece that survived exclusion must still match at least one include
pattern. If include filters are absent, surviving pieces are valid.

Packing never mixes valid and invalid pieces in one combined chunk.

### 5.3 Packing

When a budget is active, consecutive pieces of the same file that share
the same validity flag are joined with a blank-line separator until the
next join would exceed the budget. Packing does not cross file or
section boundaries.

Two greedy directions are computed, forward and backward. The chosen
packing is the one with fewer packs; ties prefer the forward result
unless the backward score is strictly better. The score is the pack
count, then the negation of the smallest pack length, so a direction
that avoids a tiny leftover wins when counts are equal in spirit.

### 5.4 Hard cap and size notes

More than 200 chunks in one run is a hard error. The message tells the
operator to refine patterns or process fewer files.

Final chunks shorter than 50 characters produce an INFO note under
`--verbose`. Final chunks still above the active budget produce an INFO
note under `--verbose`. These notes do not point at `--debug`.

`--debug` traces, per section and file, the pattern index, input
length, piece counts, filter valid/invalid counts, pack direction and
final min/max lengths. Debug traces do not dump chunk payloads.

### 5.5 Simulate board counts

The simulate run board shows `small / over` for the finished chunk
list. `small` uses the same 50-character threshold as the tokenizer.
`over` uses the active global pack budget when that budget is set and
positive. The board does not advertise debug mode.

### 5.6 Worked narrative for this document

Suppose this profile is the only resource file and the resource section
says:

```toml
regex_patterns = ['^##\s+', '^###\s+']
pack_limit_chars = 4000
```

Pattern 0 cuts on `##` chapter titles. Chapter 5 as a single piece is
larger than 4000 characters, so pattern 1 cuts on `###` section titles.
Sections that still exceed 4000 characters remain whole. Consecutive
small sections of the same file may then pack until the budget fills.

The operator can count:

- chapters at `##` as the coarse partition
- sections at `###` as the overflow partition
- final packed chunks on the board

That count is the demonstration the example exists to make.


#### REQ-CHK-001 — First pattern always cuts

**Statement.** The first compiled pattern in `regex_patterns` shall be applied to the whole file text even when no pack budget is set.

**Rationale.** Coarse structure must be available without packing.

**Acceptance criteria.**

1. A heading pattern splits a Markdown file in simulation with pack unset.
2. Capturing groups do not change the cut position; the match start does.
3. The matched heading text belongs to the piece that follows the cut.

#### REQ-CHK-002 — Later patterns are overflow only

**Statement.** Patterns after the first shall run only against pieces that still exceed the active character budget.

**Rationale.** Unconditional deep splitting destroys packing and explodes chunk counts.

**Acceptance criteria.**

1. With pack unset or 0, a second pattern does not refine pieces.
2. With pack set to a value smaller than a chapter, the second pattern is attempted on that chapter.
3. A no-op overflow pattern is skipped in favour of the next pattern and this is visible at DEBUG.

#### REQ-CHK-003 — Packing stays inside one file

**Statement.** Joining of pieces shall not combine text from two files or two resource sections.

**Rationale.** Output filenames and activity traces key off file and section.

**Acceptance criteria.**

1. Two short files under the same section remain two chunks after packing.
2. Valid and invalid neighbours are not joined.

#### REQ-CHK-004 — Circuit breaker at 200 chunks

**Statement.** Producing more than 200 chunks shall abort the run.

**Rationale.** A runaway regex is an availability incident, not a feature.

**Acceptance criteria.**

1. The error names the hard limit.
2. The error advises refining patterns or processing fewer files.

#### REQ-CHK-005 — Verbose notes describe final chunks

**Statement.** Size notes at INFO shall refer to chunks after split, filter and pack, not to intermediate overflow pieces that packing will absorb.

**Rationale.** Operators act on what sessions will see.

**Acceptance criteria.**

1. A tiny piece that is packed into a larger neighbour does not by itself create an INFO undersize note.
2. A leftover piece above the budget after every overflow pattern does create an INFO oversize note.
3. INFO text does not mention `--debug` or `-d`.

### 5.7 Invalid regular expressions

A pattern that does not compile raises a tokenizer error that names the
section and the index inside `regex_patterns`. The run must not start
completions after that failure.

### 5.8 Character budget sources

The effective budget is taken from the execution setting
`pack_limit_chars` when that setting is set. A value `<= 0` means no
budget. Otherwise the section's own `pack_limit_chars` is used if it is
a positive integer. Debug logs record whether the budget came from the
global setting, the section, or is off.

### 5.9 Why two greedy directions exist

Heading-oriented splits often leave a short preface before the first
heading and a short coda after the last. Packing only forward can trap
a tiny preface as its own chunk. Packing backward can absorb that
preface into the following body, or the reverse. Choosing the better
of the two is a small hedge, not a general optimisation framework.

---

## 6. Prompt templates and session assembly

### 6.1 Template files

A prompt file is TOML. It carries system instruction text, how material
is framed, optional synthesis instruction, temperature-related
defaults where the template is allowed to speak, a sequential-
processing flag, an output filename schema for directory writes, and an
output delimiter for concatenated results.

The operator may also pass `-t` with a literal task string instead of a
prompt file for small experiments. That path is secondary. Production
runs are expected to version-control a prompt file.

### 6.2 Placeholders

Templates may reference chunk fields such as filename and numeric
identifiers, loop fields from a text line or a JSONL object, a
timestamp, and `{STDIN}` when standard input is part of the contract.
Unknown placeholders must not crash in an undefined way; filename
formatting falls back to a stable `session_NNNN.md` or `output.md`
style name when formatting fails.

### 6.3 Sequential versus batched

When sequential processing is on, each valid chunk is a session (times
the loop cardinality). When it is off, chunks are assembled together
into fewer sessions according to the template. The simulate board
labels the mode `sequential` or `batched`.

### 6.4 Invalid chunks

Invalid chunks remain visible in material counts but are not the text
the model is asked to answer about. Filters exist precisely so that
boilerplate or excluded sections do not consume the window.


#### REQ-PMT-001 — Templates are files

**Statement.** The preferred prompt input shall be a TOML file passed with `-p`.

**Rationale.** Prompts are code and must be reviewable.

**Acceptance criteria.**

1. A missing prompt file when `-p` is required fails the run.
2. `-t` remains available as a short task string.

#### REQ-PMT-002 — Filename schema is constrained

**Statement.** Directory output names shall be sanitised and kept inside the destination directory.

**Rationale.** A placeholder must not become a path escape.

**Acceptance criteria.**

1. A crafted chunk filename cannot write outside `-O`.
2. Name collisions in exclusive mode fail without deleting already staged successes.

---

## 7. Loop iteration

### 7.1 Loop sources

A loop file may be plain text or JSONL. Text lines become iteration
records. JSONL objects expose every key as a placeholder. An empty or
absent loop yields a single implicit pass so that material-only runs
still work.

### 7.2 Cardinality

Session count is a function of sequential mode, valid chunks and loop
lines. The simulate board shows sessions, chunks, files, valid chunks
and loop items so the operator can check the multiplication before
paying for it.

### 7.3 Loop identifiers

Loop records expose a numeric identifier and a content or id string
used in output names and session boards. Formatting coerces numeric
fields so that `{LOOP_NUM_ID:04d}` works.


#### REQ-LOP-001 — JSONL keys become placeholders

**Statement.** Each key of a JSONL loop object shall be available to the template as a placeholder.

**Rationale.** The marketing sample depends on this.

**Acceptance criteria.**

1. A key `audience` can be interpolated where the template asks for it.
2. Missing keys do not invent values from another row.

---

## 8. Execution modes: simulate, live, sequential, batched

### 8.1 Simulation

Simulation is a first-class mode, not a debug leftover. It is triggered
by the simulate setting or by mock finish reasons. It must never open
the live completions path.

The TTY run board is a framed four-column Markdown table. File output
uses the same facts without the TTY frame where that distinction
already exists. Per-session file bodies in simulate mode are the
session board plus a role/content payload table. Live model text is
not mixed into those boards.

### 8.2 Live streaming

Live calls stream. A verbose heartbeat every ten seconds while a
completion is still streaming tells the operator that a local model has
not died. The heartbeat is a log line, not a stdout spinner.

### 8.3 Sequential and batched together with loops

Sequential mode multiplies sessions. Batched mode collapses chunks and
then multiplies by loop lines. Operators are expected to read the
board rather than guess.


#### REQ-EXE-001 — Simulate never calls the model

**Statement.** When simulate is enabled, the process shall not perform a live chat-completions request.

**Rationale.** The manual's first workflow is a dry run.

**Acceptance criteria.**

1. No HTTP request to `base_url` is required for a successful simulate run that only needs boards.
2. Stdout starts with the run board, not with model prose.

#### REQ-EXE-002 — Verbose heartbeat stays off stdout

**Statement.** The ten-second streaming heartbeat shall go to the logger, not to the result stream.

**Rationale.** Stdout is for results and boards; mixing a spinner breaks pipes.

**Acceptance criteria.**

1. A piped simulate or live run does not contain heartbeat text in the result body.

---

## 9. Context-window estimation

### 9.1 Inputs

Estimation uses `chars_per_token`, `max_context_tokens` and
`max_output_tokens`. When all three are set, a validation report can be
written to the activity file with per-session estimates and a run
summary.

### 9.2 Board fields

The simulate board shows pack budget, window yes/no/n/a, peak tokens
versus limit, and the session index where the peak occurred, plus the
count of context-window warnings. Those warnings are distinct from
chunk size flags.

### 9.3 Honesty

Estimation is a character heuristic, not a vendor tokeniser. The
profile forbids presenting the estimate as an exact vendor bill.


#### REQ-CTX-001 — Window facts are optional but consistent

**Statement.** When the three estimation settings are absent, board window fields shall show the documented empty markers rather than fabricated numbers.

**Rationale.** Missing configuration must look like missing configuration.

**Acceptance criteria.**

1. Peak and limit render as `--` when no report exists.
2. Window renders as `n/a` when unknown, `yes` when valid, `no` when not.

---

## 10. Output routing, modes and staging

### 10.1 Destinations

A run always prints something to stdout: the board in simulate mode,
or the joined model text otherwise. Independently, `-o` may write one
file and `-O` may write a directory of files.

### 10.2 Open modes

`x` creates exclusively and is the default. `w` overwrites. `a`
appends. Exclusive mode is the safe default because repeating a run
must not clobber a paid result by accident.

### 10.3 Directory staging

Directory writes assemble files in a hidden staging directory under
the target and then commit. If a final-name conflict occurs in
exclusive mode, the failure names the staging location so the operator
can recover the generated text. That behaviour exists because a lost
batch after a long live run is more expensive than a leftover
directory.

### 10.4 Delimiters and schemas

Several results in one file are joined with the configured delimiter.
Directory names come from the prompt's output filename schema after
sanitisation.


#### REQ-OUT-001 — Exclusive create is the default

**Statement.** When the operator does not set an output mode, the writer shall use exclusive create.

**Rationale.** Paid text should not vanish behind an accidental rerun.

**Acceptance criteria.**

1. Default mode is `x`.
2. A collision in `x` fails the write rather than appending.

#### REQ-OUT-002 — Staging preserves generated text

**Statement.** A failed commit from staging to the target directory shall leave the generated files in the staging directory and say so.

**Rationale.** Recovery beats a clean empty failure.

**Acceptance criteria.**

1. The error text contains the staging path.
2. Successful commits remove the staging directory.

---

## 11. Configuration surface

### 11.1 Origins

Four origins exist: CLI, config file, environment, default. The
default user file is `~/.config/dragiter/config.toml` when neither
`-c` nor `DRAGITER_CONFIG_FILE` is set.

Relative `-c` paths resolve against `-b` when `-b` is set.

### 11.2 Flags that matter to this example

- `-s` simulate
- `-v` verbose (INFO)
- `-d` debug
- `-r` resource file
- `-p` prompt file
- `-l` loop file
- `--pack-limit-chars` global budget, overrides the section
- `-o` / `-O` / `-m` output
- `-a` activity
- `-b` base directory

### 11.3 Environment names

Environment names follow the `DRAGITER_` prefix documented in the man
page. This profile does not duplicate the full list. It does require
that boolean parsing stays strict.


#### REQ-CFG-001 — Global pack budget overrides the section

**Statement.** When `pack_limit_chars` is set globally, including to `0`, the section value shall not apply.

**Rationale.** One switch must be able to disable packing for a whole run.

**Acceptance criteria.**

1. CLI `--pack-limit-chars 0` disables overflow patterns after the first even if the section lists a positive budget.
2. CLI `--pack-limit-chars 4000` applies 4000 even if the section lists another figure.

---

## 12. Providers, transport, retry and TLS

### 12.1 Protocol

dragiter speaks OpenAI-compatible chat completions. Switching provider
means switching `base_url`, `model_name` and `api_key`. Examples ship
sample configs for Ollama, Google-compatible gateways, Grok and Claude
gateways as the repository maintains them.

### 12.2 Streaming and usage

Live completions stream. Usage readers accept both
`prompt_tokens`/`completion_tokens` and `input_tokens`/`output_tokens`
so that providers that renamed the fields still fill the result.

### 12.3 Retry policy

`max_retry` is an attempt count, not a number of extras. Unset or `0`
means one try. Allowed range is 0–9. `retry_delay` is the base wait
before attempt 2 and later; it doubles each time. Unset uses 3 seconds
at runtime; allowed range is 0–20.

Retried conditions are connection failures and selected transient
status codes (500, 502, 503 and 429 as implemented). 504, gateway
timeout and runner-crash classes are terminal. The SDK's own retry
counter is left at zero so dragiter owns the policy.

### 12.4 TLS

A custom CA bundle path is supported. Client certificate and key paths
enable mutual TLS. TCP keep-alive can be enabled on the HTTP
transport.


#### REQ-NET-001 — Keys never belong in committed configs

**Statement.** Example configuration files shall not contain real secrets. Field names containing `key` shall be masked in activity records.

**Rationale.** The manual's security how-to is part of the product.

**Acceptance criteria.**

1. An activity record shows `***MASKED***` for `api_key`.
2. Documented examples use placeholders, not live credentials.

#### REQ-NET-002 — Retry does not loop forever

**Statement.** Attempt count shall be capped by `max_retry` in the documented range.

**Rationale.** Local models fail; unbounded retry hides that.

**Acceptance criteria.**

1. A permanent 500 stops after the configured attempts.
2. A 504 does not consume the full retry budget if it is classified terminal.

---

## 13. Observability: logs, boards and activity files

### 13.1 Log levels

Default level is WARNING. `--verbose` / `-v` raises the console to
INFO. `--debug` / `-d` raises it to DEBUG. Debug includes verbose.

Chunk-quality notes are INFO so a quiet default run stays quiet.
Path-escape skips remain warnings. Hard failures remain exceptions.

### 13.2 Boards

The run board is a fixed-width four-column Markdown table. Cells clip
with an ellipsis when they exceed the column width. The board is the
operator's one-glance checksum of a simulate run.

### 13.3 Activity file

`-a` appends JSONL records for auditable stages: settings (masked),
resources, material summaries, context reports when present. Resource
records include `regex_patterns` and do not include `regex_pattern`.


#### REQ-OBS-001 — Three channels stay decoupled

**Statement.** The simulate board, verbose INFO notes and debug traces shall not advertise one another.

**Rationale.** Each flag has one job.

**Acceptance criteria.**

1. The board has no `use -d` hint.
2. INFO size notes have no `use -d` hint.
3. DEBUG traces carry counts and lengths, not full chunk text.

---

## 14. Security requirements

### 14.1 Path safety

Output paths are forced to remain inside the chosen directory.
Resource discovery blocks relative escapes from the section root.
Filename sanitisation strips control characters and hostile path
pieces from generated names.

### 14.2 Secrets

API keys belong in the environment or a file mode that the operator
controls. Activity logs mask key-like fields. URLs in logs must not be
used as a side channel for secrets.

### 14.3 Least surprise

Exclusive create, deny-by-default path containment, and a hard chunk
cap are security-adjacent reliability controls. They stay on unless
the operator chooses a looser output mode.


#### REQ-SEC-001 — Directory output cannot escape

**Statement.** A generated file path shall be rejected if it is not inside the `-O` directory after resolution.

**Rationale.** Placeholders expand operator-controlled text.

**Acceptance criteria.**

1. A chunk filename containing `..` does not write outside the destination.

---

## 15. Command-line and operator experience

### 15.1 Help surfaces

`-h` is the short argparse help. `--info` is the long man-page text.
`--version` prints the package version.

### 15.2 First-run path

The documented first-run path is: generate examples, simulate, then
run against a local Ollama config with `-v`. This profile treats that
order as a requirement on the examples remaining runnable.

### 15.3 Silence versus noise

Local models can sit on a stream for a long time. Verbose mode exists
so that silence is not mistaken for a hang. Debug mode exists so that
a regex waterfall can be counted. Neither mode is the default.


#### REQ-CLI-001 — Examples remain the tutorial

**Statement.** Shipped examples shall use `regex_patterns` lists and shall simulate without a network.

**Rationale.** A broken example is a broken tutorial.

**Acceptance criteria.**

1. Example resource files do not contain `regex_pattern`.
2. `dragiter -s` on an official example exits 0 on a clean tree.

---

## 16. Quality attributes

### 16.1 Reproducibility

Same inputs, same settings, same assembled messages. Temperature
defaults in samples are often `0.0` for that reason. Live model
sampling still belongs to the provider; dragiter's determinism claim
stops at the request payload.

### 16.2 Operability

Boards, INFO notes, DEBUG traces, activity files and explicit exit
codes are the operability surface. They must stay aligned with the
same chunk counters.

### 16.3 Maintainability

British English in product documentation and source comments. No
German in code. External API names such as a third-party
`initialize()` stay as the library spelled them.

### 16.4 Performance

dragiter is bounded by model latency, not by a need to parse million-
file monorepos in one process. The 200-chunk cap is an honesty device.
Operators with larger corpora split the work across invocations.

### 16.5 Portability

POSIX-style paths are the development baseline. Absolute glob escape
hatches mention Windows anchors in comments because `Path.anchor`
exists. This profile does not claim a first-class Windows GUI.


#### REQ-QA-001 — Counters agree

**Statement.** The number of final chunks on the simulate board shall equal the number of chunks the tokenizer returned for that run.

**Rationale.** A board that disagrees with the tokenizer is a defect.

**Acceptance criteria.**

1. Adding a second overflow pattern that creates new cuts increases the pre-pack piece count in DEBUG.
2. Packing may reduce the final chunk count; the board shows the final count.

---

## 17. Acceptance matrix for the staged-regex example

### 17.1 What the example must prove

The example in `examples/04_textmeter_sample` exists to make
`regex_patterns` countable:

1. A first pattern that cuts on `## ` produces one piece per chapter
   plus any preface before the first chapter.
2. With a pack budget smaller than this chapter, a second pattern that
   cuts on `### ` increases the piece count inside this chapter.
3. With pack unset, the second pattern does not run, so the piece count
   stays at the chapter grain.
4. Verbose INFO reports undersized or over-budget *final* chunks.
5. Debug traces mention pattern indices `1/2` and `2/2`.
6. The simulate board `small / over` column is an integer pair.

### 17.2 Suggested measurement procedure

Run once with only the first pattern and no budget. Record sessions
and chunks from the board. Run again with both patterns and
`pack_limit_chars = 4000`. Record the new chunk count. The second run
must show more pieces before packing inside chapter 5, and the debug
log must show overflow refine lines. That difference is the acceptance
signal.

### 17.3 What would fail the example

- shipping `regex_pattern` in the example resource file
- a board hint that says `use -d`
- INFO notes that dump the requirements text
- a document so short that one pattern already yields pieces under the
  budget, so the second pattern never runs


#### REQ-ACC-001 — Second pattern is observable

**Statement.** On this requirements file, enabling a second heading pattern under a 4000-character budget shall change DEBUG piece counts relative to a first-pattern-only run.

**Rationale.** Unobservable features do not belong in an example.

**Acceptance criteria.**

1. DEBUG contains a primary-pattern line and at least one overflow-pattern line for chapter 5.
2. The simulate board still prints `small / over`.

---

## 18. Non-goals, exclusions and rejected ideas

### 18.1 Rejected: keep the singular key forever

The singular TOML key is gone. Compatibility is not silent. Operators
must edit resource files. Examples and tests must already show the
list form.

### 18.2 Rejected: warn at 20 000 characters regardless of budget

A fixed ceiling fought the pack budget. Size notes now use the active
budget for oversize and 50 characters for undersize.

### 18.3 Rejected: chat UI, hosted control plane, plugins

Those would change the product identity. They are non-goals.

### 18.4 Rejected: dumping payloads at DEBUG

Debug is for counts. Payload text belongs in simulate transcripts when
the operator asked for simulate output files.

---

## 19. Glossary

### 19.1 Terms

**Chunk.** A piece of file text after split, filter and optional pack.

**Section.** A table in the resource TOML, also the name stamped on
chunks from that table.

**Pack budget.** `pack_limit_chars`, global or per section.

**Staged patterns.** `regex_patterns[0]` always; later entries only on
overflow.

**Simulate board.** The four-column Markdown run summary.

**Activity file.** JSONL audit trail requested with `-a`.

**Valid chunk.** A chunk that passed exclude/include filters.

**Origin.** The source of a setting: CLI, config, environment, default.

### 19.2 Abbreviations

CLI, CWD, JSONL, mTLS, TOML, TTY, INFO, DEBUG, WARNING.

---

## 20. Traceability and document control

### 20.1 Sources

This profile is traced to:

- the package README
- `docs/manual.md`
- `docs/reference.md`
- `docs/info.txt`
- the pipeline workers for resource collection, material tokenisation
  and output writing as they stand after the `regex_patterns`-only
  change

### 20.2 Change rules

When behaviour changes, this profile changes in the same commit as the
example resource file whenever the example would otherwise lie. A
heading-level change that breaks the sample patterns is a breaking
change for the example and must be called out.

### 20.3 Measurement appendix intent

A later README in this example directory will record the exact
commands and the expected direction of the counts. This chapter only
states that such a measurement is required.


---

## 21. Material formats and encodings

### 21.1 Text files only

The collector keeps files the encoding detector accepts. Binary assets are skipped. Markdown is the usual demonstration format because heading anchors make regular expressions obvious. C source and JSONL loops exist as additional official samples.

#### REQ-211 — Text files only

**Statement.** The collector keeps files the encoding detector accepts.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 21.2 Encoding failures are local

A single undecodable file does not fail the run. It is omitted and a debug line records the skip. Operators who need a hard fail on encoding must wrap the tool.

#### REQ-212 — Encoding failures are local

**Statement.** A single undecodable file does not fail the run.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 21.3 Path spelling

Chunk filenames store the POSIX form of the path as collected. Output schemas that interpolate `{CHUNK_FILE_NAME}` receive a sanitised form, not a raw path with separators left intact.

#### REQ-213 — Path spelling

**Statement.** Chunk filenames store the POSIX form of the path as collected.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

---

## 22. Filters in operational detail

### 22.1 Exclude first

Exclude is a veto. An excluded piece is invalid even if an include pattern would also match. This is the documented 'exclude first' rule.

#### REQ-221 — Exclude first

**Statement.** Exclude is a veto.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 22.2 Include as permission

When include filters exist, a piece must match at least one. When they do not exist, exclusion is the only gate.

#### REQ-222 — Include as permission

**Statement.** When include filters exist, a piece must match at least one.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 22.3 Case and multiline

Filter searches use multiline and case-insensitive flags. Authors should not assume POSIX case-folding beyond that.

#### REQ-223 — Case and multiline

**Statement.** Filter searches use multiline and case-insensitive flags.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

---

## 23. Placeholders and filename schemas

### 23.1 Chunk fields

Numeric chunk identifiers and sanitised file and section names are the supported chunk placeholders. Missing numbers become 0 rather than raising during name format.

#### REQ-231 — Chunk fields

**Statement.** Numeric chunk identifiers and sanitised file and section names are the supported chunk placeholders.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 23.2 Loop fields

Keys ending in `_NUM_ID` and `LOOP_NUM_ID` are forced to int when possible so format specifiers work.

#### REQ-232 — Loop fields

**Statement.** Keys ending in `_NUM_ID` and `LOOP_NUM_ID` are forced to int when possible so format specifiers work.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 23.3 Timestamp

A sortable UTC timestamp with nanosecond padding exists for unique names. It is lexicographically sortable.

#### REQ-233 — Timestamp

**Statement.** A sortable UTC timestamp with nanosecond padding exists for unique names.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

---

## 24. Failure modes the operator will actually see

### 24.1 Removed key

The collection error for `regex_pattern` is the failure this example exists to contrast against. The example file must not commit that key.

#### REQ-241 — Removed key

**Statement.** The collection error for `regex_pattern` is the failure this example exists to contrast against.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 24.2 Bad regex

Compile failures name `regex_patterns[i]` and the section.

#### REQ-242 — Bad regex

**Statement.** Compile failures name `regex_patterns[i]` and the section.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 24.3 Chunk cap

The 200-chunk error is the backstop if someone points the second pattern at every line of this profile.

#### REQ-243 — Chunk cap

**Statement.** The 200-chunk error is the backstop if someone points the second pattern at every line of this profile.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 24.4 Exclusive collision

Mode `x` plus a name that already exists is a failed write with staging recovery for directory output.

#### REQ-244 — Exclusive collision

**Statement.** Mode `x` plus a name that already exists is a failed write with staging recovery for directory output.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

---

## 25. Relationship to official samples

### 25.1 Markdown sample

Example 01 splits historical Markdown by headings and numbered lines across two sections.

#### REQ-251 — Markdown sample

**Statement.** Example 01 splits historical Markdown by headings and numbered lines across two sections.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 25.2 C sample

Example 02 uses two sections on the same tree: function-like lines and documented header sections.

#### REQ-252 — C sample

**Statement.** Example 02 uses two sections on the same tree: function-like lines and documented header sections.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 25.3 JSONL sample

Example 03 loops target groups over a specification document.

#### REQ-253 — JSONL sample

**Statement.** Example 03 loops target groups over a specification document.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

### 25.4 This sample

Example 04 is a single long specification whose chapter grain is coarser than the pack budget. That is the only new claim.

#### REQ-254 — This sample

**Statement.** Example 04 is a single long specification whose chapter grain is coarser than the pack budget.

**Rationale.** Operational detail required so the example stays honest.

**Acceptance criteria.**

1. Behaviour matches the technical reference for this topic.
2. The example README may cite this section when explaining counts.

---

## 26. Requirements index (normative restatement)

### 26.1 How to read this index

Each row restates a rule already given. The index exists so that a
split on `###` yields many similarly sized blocks after chapter 26 is
cut from chapter 25. Blocks are still about dragiter. They are not
random text.


### 26.2 CLI precedes config

#### REQ-IDX-001 — CLI precedes config

**Statement.** A flag on the command line wins over the same key in the TOML configuration file.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.2`.

### 26.3 Config precedes environment

#### REQ-IDX-002 — Config precedes environment

**Statement.** A value in the selected config file wins over `DRAGITER_*`.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.3`.

### 26.4 Environment precedes default

#### REQ-IDX-003 — Environment precedes default

**Statement.** An explicit environment value wins over a built-in default.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.4`.

### 26.5 Simulate flag

#### REQ-IDX-004 — Simulate flag

**Statement.** `-s` disables live completions for the run.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.5`.

### 26.6 Verbose flag

#### REQ-IDX-005 — Verbose flag

**Statement.** `-v` sets console logging to INFO.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.6`.

### 26.7 Debug flag

#### REQ-IDX-006 — Debug flag

**Statement.** `-d` sets console logging to DEBUG.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.7`.

### 26.8 Log file

#### REQ-IDX-007 — Log file

**Statement.** `-L` appends the same level to a file without rotation.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.8`.

### 26.9 Base directory flag

#### REQ-IDX-008 — Base directory flag

**Statement.** `-b` is the global rebase root and starts unset.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.9`.

### 26.10 Pack flag

#### REQ-IDX-009 — Pack flag

**Statement.** `--pack-limit-chars` overrides section budgets, including when set to 0.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.10`.

### 26.11 Prompt flag

#### REQ-IDX-010 — Prompt flag

**Statement.** `-p` names the prompt TOML file.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.11`.

### 26.12 Task flag

#### REQ-IDX-011 — Task flag

**Statement.** `-t` supplies a literal task string.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.12`.

### 26.13 Resource flag

#### REQ-IDX-012 — Resource flag

**Statement.** `-r` names the resource TOML file.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.13`.

### 26.14 Loop flag

#### REQ-IDX-013 — Loop flag

**Statement.** `-l` names a `.txt` or `.jsonl` loop file.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.14`.

### 26.15 Output file flag

#### REQ-IDX-014 — Output file flag

**Statement.** `-o` writes one result file.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.15`.

### 26.16 Output directory flag

#### REQ-IDX-015 — Output directory flag

**Statement.** `-O` writes many result files.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.16`.

### 26.17 Output mode flag

#### REQ-IDX-016 — Output mode flag

**Statement.** `-m` selects `x`, `w` or `a`.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.17`.

### 26.18 Activity flag

#### REQ-IDX-017 — Activity flag

**Statement.** `-a` writes JSONL activity records.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.18`.

### 26.19 Model name

#### REQ-IDX-018 — Model name

**Statement.** `--model-name` is the provider model identifier.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.19`.

### 26.20 Base URL

#### REQ-IDX-019 — Base URL

**Statement.** `--base-url` is the OpenAI-compatible endpoint.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.20`.

### 26.21 API key

#### REQ-IDX-020 — API key

**Statement.** `--api-key` is the secret; prefer the environment.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.21`.

### 26.22 Temperature

#### REQ-IDX-021 — Temperature

**Statement.** `--temperature` defaults toward deterministic samples in examples.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.22`.

### 26.23 Chars per token

#### REQ-IDX-022 — Chars per token

**Statement.** Used only for estimation, not for billing.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.23`.

### 26.24 Max context tokens

#### REQ-IDX-023 — Max context tokens

**Statement.** Total window including reserved output.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.24`.

### 26.25 Max output tokens

#### REQ-IDX-024 — Max output tokens

**Statement.** Reservation subtracted from the window.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.25`.

### 26.26 Retry delay

#### REQ-IDX-025 — Retry delay

**Statement.** Base seconds before attempt 2; doubles later.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.26`.

### 26.27 Max retry

#### REQ-IDX-026 — Max retry

**Statement.** Attempt count in 0–9; 0 means one try.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.27`.

### 26.28 CA bundle

#### REQ-IDX-027 — CA bundle

**Statement.** Optional PEM trust store.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.28`.

### 26.29 Client certificate

#### REQ-IDX-028 — Client certificate

**Statement.** Optional PEM for mTLS.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.29`.

### 26.30 Client key

#### REQ-IDX-029 — Client key

**Statement.** Optional PEM private key for mTLS.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.30`.

### 26.31 TCP keep-alive

#### REQ-IDX-030 — TCP keep-alive

**Statement.** Optional httpx2 transport flag.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.31`.

### 26.32 Sequential processing

#### REQ-IDX-031 — Sequential processing

**Statement.** One request per chunk instead of a batch.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.32`.

### 26.33 Output delimiter

#### REQ-IDX-032 — Output delimiter

**Statement.** Inserted between concatenated results.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.33`.

### 26.34 Filename schema

#### REQ-IDX-033 — Filename schema

**Statement.** Template for `-O` names.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.34`.

### 26.35 Help flag

#### REQ-IDX-034 — Help flag

**Statement.** `-h` prints short help.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.35`.

### 26.36 Info flag

#### REQ-IDX-035 — Info flag

**Statement.** `--info` prints the man-page text.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.36`.

### 26.37 Version flag

#### REQ-IDX-036 — Version flag

**Statement.** `--version` prints the package version.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.37`.

### 26.38 Gen docs

#### REQ-IDX-037 — Gen docs

**Statement.** `dragiter-gen-docs` extracts documentation.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.38`.

### 26.39 Gen examples

#### REQ-IDX-038 — Gen examples

**Statement.** `dragiter-gen-examples` extracts samples.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.39`.

### 26.40 Exit 0

#### REQ-IDX-039 — Exit 0

**Statement.** Success.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.40`.

### 26.41 Exit 1

#### REQ-IDX-040 — Exit 1

**Statement.** Configuration or critical error.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.41`.

### 26.42 Exit 130

#### REQ-IDX-041 — Exit 130

**Statement.** Keyboard interrupt.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.42`.

### 26.43 User config path

#### REQ-IDX-042 — User config path

**Statement.** `~/.config/dragiter/config.toml` is the default file.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.43`.

### 26.44 Boolean env parsing

#### REQ-IDX-043 — Boolean env parsing

**Statement.** Only the documented truthy and falsy tokens are accepted.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.44`.

### 26.45 TOML booleans

#### REQ-IDX-044 — TOML booleans

**Statement.** Config-file booleans must be native, not quoted strings.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.45`.

### 26.46 Resource tables

#### REQ-IDX-045 — Resource tables

**Statement.** Each TOML table is one section.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.46`.

### 26.47 Glob list

#### REQ-IDX-046 — Glob list

**Statement.** `glob_patterns` selects candidate files.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.47`.

### 26.48 Section base

#### REQ-IDX-047 — Section base

**Statement.** Optional per-section search root.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.48`.

### 26.49 Regex list

#### REQ-IDX-048 — Regex list

**Statement.** `regex_patterns` is the only regex key.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.49`.

### 26.50 Removed key

#### REQ-IDX-049 — Removed key

**Statement.** `regex_pattern` aborts collection.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.50`.

### 26.51 Include filters

#### REQ-IDX-050 — Include filters

**Statement.** Optional permission list.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.51`.

### 26.52 Exclude filters

#### REQ-IDX-051 — Exclude filters

**Statement.** Optional veto list.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.52`.

### 26.53 Section pack

#### REQ-IDX-052 — Section pack

**Statement.** Optional per-section character budget.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.53`.

### 26.54 Default regex

#### REQ-IDX-053 — Default regex

**Statement.** Omitted list becomes a never-match pattern.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.54`.

### 26.55 Match-start cuts

#### REQ-IDX-054 — Match-start cuts

**Statement.** Cuts use `match.start()`, not group spans.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.55`.

### 26.56 Groups ignored

#### REQ-IDX-055 — Groups ignored

**Statement.** Capturing groups do not steer the knife.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.56`.

### 26.57 Overflow gated

#### REQ-IDX-056 — Overflow gated

**Statement.** Later patterns need a live budget and an oversized piece.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.57`.

### 26.58 No-op pattern

#### REQ-IDX-057 — No-op pattern

**Statement.** A pattern that does not cut yields to the next.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.58`.

### 26.59 Intact leftover

#### REQ-IDX-058 — Intact leftover

**Statement.** An irreducible piece stays whole.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.59`.

### 26.60 Pack separator

#### REQ-IDX-059 — Pack separator

**Statement.** Joined pieces use a blank line between them.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.60`.

### 26.61 Same validity

#### REQ-IDX-060 — Same validity

**Statement.** Packing will not mix valid and invalid pieces.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.61`.

### 26.62 Same file

#### REQ-IDX-061 — Same file

**Statement.** Packing will not cross file boundaries.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.62`.

### 26.63 Forward pack

#### REQ-IDX-062 — Forward pack

**Statement.** Greedy left-to-right join under the budget.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.63`.

### 26.64 Backward pack

#### REQ-IDX-063 — Backward pack

**Statement.** Greedy right-to-left join under the budget.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.64`.

### 26.65 Pack choice

#### REQ-IDX-064 — Pack choice

**Statement.** Fewer packs win; then avoid a tiny leftover.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.65`.

### 26.66 Chunk cap

#### REQ-IDX-065 — Chunk cap

**Statement.** More than 200 chunks is fatal.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.66`.

### 26.67 Min size note

#### REQ-IDX-066 — Min size note

**Statement.** Final chunks under 50 characters log INFO.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.67`.

### 26.68 Oversize note

#### REQ-IDX-067 — Oversize note

**Statement.** Final chunks over the budget log INFO.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.68`.

### 26.69 No debug ads

#### REQ-IDX-068 — No debug ads

**Statement.** INFO and the board do not mention `-d`.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.69`.

### 26.70 Debug counts

#### REQ-IDX-069 — Debug counts

**Statement.** DEBUG lines carry lengths and counts only.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.70`.

### 26.71 Board small/over

#### REQ-IDX-070 — Board small/over

**Statement.** Simulate board prints those two integers.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.71`.

### 26.72 Board window

#### REQ-IDX-071 — Board window

**Statement.** Separate from chunk size flags.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.72`.

### 26.73 Mock finish

#### REQ-IDX-072 — Mock finish

**Statement.** Finish reason `mock` is treated as simulation.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.73`.

### 26.74 Streaming live

#### REQ-IDX-073 — Streaming live

**Statement.** Live completions use the streaming client.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.74`.

### 26.75 Heartbeat

#### REQ-IDX-074 — Heartbeat

**Statement.** Ten-second INFO pulse while a stream is open.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.75`.

### 26.76 Usage aliases

#### REQ-IDX-075 — Usage aliases

**Statement.** Both token field namings are read.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.76`.

### 26.77 Retry ownership

#### REQ-IDX-076 — Retry ownership

**Statement.** Provider SDK retries stay at zero.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.77`.

### 26.78 Transient retry

#### REQ-IDX-077 — Transient retry

**Statement.** Connection errors and selected 5xx/429 retry.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.78`.

### 26.79 Terminal 504

#### REQ-IDX-078 — Terminal 504

**Statement.** Gateway timeout does not masquerade as retryable.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.79`.

### 26.80 Masked keys

#### REQ-IDX-079 — Masked keys

**Statement.** Activity fields whose names contain `key` are masked.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.80`.

### 26.81 Path contain

#### REQ-IDX-080 — Path contain

**Statement.** Relative resource matches must stay in root.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.81`.

### 26.82 Abs glob hatch

#### REQ-IDX-081 — Abs glob hatch

**Statement.** Absolute globs are intentional.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.82`.

### 26.83 Output contain

#### REQ-IDX-082 — Output contain

**Statement.** `-O` targets are forced inside the directory.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.83`.

### 26.84 Sanitize names

#### REQ-IDX-083 — Sanitize names

**Statement.** Generated names cannot carry raw separators.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.84`.

### 26.85 Staging dir

#### REQ-IDX-084 — Staging dir

**Statement.** Directory writes go through a hidden staging folder.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.85`.

### 26.86 Staging keep

#### REQ-IDX-085 — Staging keep

**Statement.** Failed commits keep the staging folder.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.86`.

### 26.87 Default mode x

#### REQ-IDX-086 — Default mode x

**Statement.** Exclusive create is the default open mode.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.87`.

### 26.88 Stdin placeholder

#### REQ-IDX-087 — Stdin placeholder

**Statement.** `{STDIN}` is the documented pipe intake.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.88`.

### 26.89 JSONL loop keys

#### REQ-IDX-088 — JSONL loop keys

**Statement.** Object keys become placeholders.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.89`.

### 26.90 British docs

#### REQ-IDX-089 — British docs

**Statement.** Product documentation uses British English.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.90`.

### 26.91 AGPL licence

#### REQ-IDX-090 — AGPL licence

**Statement.** The program is AGPL-3.0-or-later.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.91`.

### 26.92 Python 3.11

#### REQ-IDX-091 — Python 3.11

**Statement.** The runtime floor is Python 3.11.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.92`.

### 26.93 CalVer

#### REQ-IDX-092 — CalVer

**Statement.** Versions look like 2026.9.8b1.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.93`.

### 26.94 Diátaxis

#### REQ-IDX-093 — Diátaxis

**Statement.** Manual and reference stay split.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.94`.

### 26.95 No chat UI

#### REQ-IDX-094 — No chat UI

**Statement.** A chat client is a non-goal.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.95`.

### 26.96 No vector store

#### REQ-IDX-095 — No vector store

**Statement.** Embeddings are a non-goal.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.96`.

### 26.97 Provider agnostic

#### REQ-IDX-096 — Provider agnostic

**Statement.** Any OpenAI-compatible endpoint is in play.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.97`.

### 26.98 Ollama demo

#### REQ-IDX-097 — Ollama demo

**Statement.** Local Ollama is the documented first live target.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.98`.

### 26.99 Examples first

#### REQ-IDX-098 — Examples first

**Statement.** Tutorial starts by generating examples.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.99`.

### 26.100 Simulate first

#### REQ-IDX-099 — Simulate first

**Statement.** Tutorial runs `-s` before a live call.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.100`.

### 26.101 Verbose locally

#### REQ-IDX-100 — Verbose locally

**Statement.** Tutorial recommends `-v` for local models.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.101`.

### 26.102 Keys not in git

#### REQ-IDX-101 — Keys not in git

**Statement.** Sample configs must not hold live secrets.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.102`.

### 26.103 Activity optional

#### REQ-IDX-102 — Activity optional

**Statement.** No activity file is written unless `-a` is set.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.103`.

### 26.104 Log optional

#### REQ-IDX-103 — Log optional

**Statement.** No log file is written unless `-L` or the env is set.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.104`.

### 26.105 CWD not implicit global base

#### REQ-IDX-104 — CWD not implicit global base

**Statement.** The global base directory stays unset until configured.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.105`.

### 26.106 Relative section rebase

#### REQ-IDX-105 — Relative section rebase

**Statement.** Only relative section bases move under `-b`.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.106`.

### 26.107 Absolute section stays

#### REQ-IDX-106 — Absolute section stays

**Statement.** An absolute section base is not rewritten by `-b`.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.107`.

### 26.108 Chunk num id

#### REQ-IDX-107 — Chunk num id

**Statement.** Chunks receive a running numeric id.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.108`.

### 26.109 Section num id

#### REQ-IDX-108 — Section num id

**Statement.** Chunks receive a per-section numeric id.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.109`.

### 26.110 Valid flag

#### REQ-IDX-109 — Valid flag

**Statement.** Each chunk carries a boolean valid flag.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.110`.

### 26.111 Material summary

#### REQ-IDX-110 — Material summary

**Statement.** Activity material records summarise counts and sizes.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.111`.

### 26.112 Context activity

#### REQ-IDX-111 — Context activity

**Statement.** When estimation settings are complete, per-session token facts can be logged.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.112`.

### 26.113 OpenAI 3 and httpx2

#### REQ-IDX-112 — OpenAI 3 and httpx2

**Statement.** Streaming requires the documented client versions.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.113`.

### 26.114 No spinner on stdout

#### REQ-IDX-113 — No spinner on stdout

**Statement.** Progress must not corrupt piped output.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.114`.

### 26.115 Four-column board

#### REQ-IDX-114 — Four-column board

**Statement.** Board cells are padded to 16 characters.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.115`.

### 26.116 Clipped cells

#### REQ-IDX-115 — Clipped cells

**Statement.** Over-wide board cells gain an ellipsis.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.116`.

### 26.117 Session board

#### REQ-IDX-116 — Session board

**Statement.** Per-session simulate files start with a compact board.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.117`.

### 26.118 Payload table

#### REQ-IDX-117 — Payload table

**Statement.** Simulate transcripts list roles as S/U/A initials.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.118`.

### 26.119 Thematic breaks

#### REQ-IDX-118 — Thematic breaks

**Statement.** Joined simulate sections use Markdown rules so tables still render.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.119`.

### 26.120 Unique names

#### REQ-IDX-119 — Unique names

**Statement.** Timestamp plus numeric ids make directory names unique enough for a run.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.120`.

### 26.121 Worker errors

#### REQ-IDX-120 — Worker errors

**Statement.** Pipeline errors wrap as named exceptions with causes.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.121`.

### 26.122 Collector error type

#### REQ-IDX-121 — Collector error type

**Statement.** Resource load failures use the collector exception type.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.122`.

### 26.123 Tokenizer error type

#### REQ-IDX-122 — Tokenizer error type

**Statement.** Split failures use the tokenizer exception type.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.123`.

### 26.124 Writer error type

#### REQ-IDX-123 — Writer error type

**Statement.** Output failures use the writer exception type.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.124`.

### 26.125 Circuit visible

#### REQ-IDX-124 — Circuit visible

**Statement.** The 200-chunk message is specific, not generic.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.125`.

### 26.126 Filter independence

#### REQ-IDX-125 — Filter independence

**Statement.** Each piece is filtered on its own text.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.126`.

### 26.127 Empty piece drop

#### REQ-IDX-126 — Empty piece drop

**Statement.** Zero-length slices after strip are not chunks.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.127`.

### 26.128 Strip on cut

#### REQ-IDX-127 — Strip on cut

**Statement.** Pieces are stripped when taken from the source text.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.128`.

### 26.129 Primary debug line

#### REQ-IDX-128 — Primary debug line

**Statement.** DEBUG names pattern 1 of n and the input length.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.129`.

### 26.130 Overflow debug line

#### REQ-IDX-129 — Overflow debug line

**Statement.** DEBUG names the later pattern index and the reduced piece count.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.130`.

### 26.131 Pack debug line

#### REQ-IDX-130 — Pack debug line

**Statement.** DEBUG names forward and backward pack counts and the winner.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.131`.

### 26.132 Section debug line

#### REQ-IDX-131 — Section debug line

**Statement.** DEBUG names file count, pattern count and budget origin.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.132`.

### 26.133 Info undersize wording

#### REQ-IDX-132 — Info undersize wording

**Statement.** The INFO text says the chunk is shorter than 50 characters.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.133`.

### 26.134 Info oversize wording

#### REQ-IDX-133 — Info oversize wording

**Statement.** The INFO text says the chunk exceeds pack_limit_chars.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.134`.

### 26.135 Board valid chunks

#### REQ-IDX-134 — Board valid chunks

**Statement.** The board also repeats the valid-chunk count beside small/over.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.135`.

### 26.136 Loop none

#### REQ-IDX-135 — Loop none

**Statement.** A run without loop lines reports loop as none on session boards.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.136`.

### 26.137 All files label

#### REQ-IDX-136 — All files label

**Statement.** Batched mode labels the file side as all files when chunks exist.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.137`.

### 26.138 Config ok header

#### REQ-IDX-137 — Config ok header

**Statement.** The framed board header reads DRAGITER / simulate on / api off / config ok.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.138`.

### 26.139 Replies column

#### REQ-IDX-138 — Replies column

**Statement.** The board reports result count against stdout brief.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.139`.

### 26.140 Output path cell

#### REQ-IDX-139 — Output path cell

**Statement.** The board shows directory if set, else file, else none.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.140`.

### 26.141 Pack off marker

#### REQ-IDX-140 — Pack off marker

**Statement.** An inactive budget renders as off on the board.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.141`.

### 26.142 Window words

#### REQ-IDX-141 — Window words

**Statement.** yes, no and n/a are the only window words.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.142`.

### 26.143 Peak markers

#### REQ-IDX-142 — Peak markers

**Statement.** Missing peak values render as --.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.143`.

### 26.144 Thousands comma

#### REQ-IDX-143 — Thousands comma

**Statement.** Board numbers use thousands separators.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.144`.

### 26.145 Example 04 grain

#### REQ-IDX-144 — Example 04 grain

**Statement.** This file's ## headings are the coarse grain.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.145`.

### 26.146 Example 04 refine

#### REQ-IDX-145 — Example 04 refine

**Statement.** This file's ### headings are the overflow grain.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.146`.

### 26.147 Example 04 length

#### REQ-IDX-146 — Example 04 length

**Statement.** Several ## chapters exceed 4000 characters on purpose.

**Rationale.** Index restatement so overflow splits remain meaningful.

**Acceptance criteria.**

1. The statement agrees with the earlier normative chapter.
2. This block remains attached to heading `### 26.147`.

---

## 27. Closing statement

### 27.1 What this profile is

A long, structured, British-English requirements profile of dragiter as
a deterministic context iterator. It is also a measuring stick: the
heading hierarchy is the example's laboratory apparatus.

### 27.2 What this profile is not

It is not a substitute for the manual or the technical reference. Where
this text and the reference disagree in a future commit, the running
code and the reference win, and this file must be updated.

### 27.3 Ready for the sample

The next artefacts in `examples/04_textmeter_sample` can now hang a
resource file and a prompt file on this document and publish the
expected chunk arithmetic in the example README.

---

## 28. Worked simulate procedure for this profile

### 28.1 First pass at chapter grain

Prepare a resource section that lists only one pattern, `^##\s+`, and
leave `pack_limit_chars` unset. Run `dragiter -s` with a trivial prompt
that echoes chunk identifiers. Record `chunks` and `small / over` from
the board. At this grain the second pattern must not appear in a debug
log because overflow is off.

#### REQ-X-28.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 28.2 Second pass with overflow

Keep the first pattern. Add `^###\s+` as `regex_patterns[1]` and set
`pack_limit_chars = 4000`. Run again with `-s -v -d`. Chapter 5 and
other long chapters must produce DEBUG lines that mention pattern 2.
The final chunk count may fall again after packing; the pre-pack piece
count in DEBUG is the number that proves the second pattern ran.

#### REQ-X-28.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 28.3 Third pass with a global zero budget

Set `--pack-limit-chars 0` while the section still lists 4000. The
global zero must disable overflow. Pattern 2 must stay silent. This
proves override semantics, not only splitting.

#### REQ-X-28.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 28.4 Reading the board without superstition

`small` is the count of final chunks under 50 characters. `over` is
the count of final chunks above the *global* budget shown on the board.
If the budget is only on the section and the CLI is unset, the board's
pack cell may read `off` even though the tokenizer packed. That
limitation is documented here so the example README does not over-claim
the board column.

#### REQ-X-28.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 28.5 What to write in the example README later

The README should publish two integer pairs: chunks and small/over
for the chapter-only run, and the same pair for the overflow run. It
should not publish golden DEBUG text dumps, because logger timestamps
move. Directional statements are enough: overflow run shows pattern
2/2 lines; zero-budget run does not.

#### REQ-X-28.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 29. Threats to measurement validity

### 29.1 Packing hides cuts

If the budget is large, overflow cuts are immediately packed back
into one chunk and the board looks unchanged. Measurement must look at
DEBUG piece counts before pack, or must choose a budget that cannot
reassemble an entire chapter.

#### REQ-X-29.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 29.2 Preface pieces

Text before the first `##` becomes its own piece. Title matter in
this file is such a preface. It may be small enough to raise `small`
on the board. That is a real signal, not a failure of the example.

#### REQ-X-29.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 29.3 Filters changing validity

An exclude filter that matches every heading would mark pieces
invalid. Packing then groups invalids separately. The example resource
should start with empty filters so the count stays about structure.

#### REQ-X-29.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 29.4 Two files instead of one

If the resource glob picks up the README as well, chunk counts
include both files. The sample glob must match only this profile
until the README says otherwise.

#### REQ-X-29.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 29.5 Circuit breaker during experiments

A pattern as broad as `^` or every line will hit the 200-chunk
cap. That abort is success of the safety requirement, not a broken
example, provided the official sample patterns stay heading-based.

#### REQ-X-29.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 30. Scenario book: first tutorial hour

### 30.1 Beat 1

The operator installs with pip, generates examples, and runs simulate on sample 01 before touching this profile. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-30.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 30.2 Beat 2

They copy an Ollama config only after the board looks sane. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-30.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 30.3 Beat 3

They never paste an API key into a file that will be committed. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-30.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 30.4 Beat 4

They learn `-v` because a local model can sit silent on a stream. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-30.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 30.5 Beat 5

They learn `-d` only when a regex does not cut where they expected. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-30.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 31. Scenario book: migrating an old resource file

### 31.1 Beat 1

A file still contains regex_pattern. Collection fails with the section name. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-31.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 31.2 Beat 2

The operator replaces the key with a one-element regex_patterns list. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-31.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 31.3 Beat 3

The same heading split returns. No silent whole-file chunk occurred. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-31.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 31.4 Beat 4

Activity JSON no longer shows a singular regex_pattern field. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-31.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 31.5 Beat 5

The changelog entry for the removal is the external explanation. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-31.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 32. Scenario book: packing a short preface

### 32.1 Beat 1

A file starts with title lines then a heading. Pattern 0 cuts at the heading. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-32.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 32.2 Beat 2

The preface is under 50 characters. Without packing it is a small chunk. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-32.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 32.3 Beat 3

Backward packing may absorb it into the following body if the budget allows. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-32.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 32.4 Beat 4

DEBUG reports which direction won. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-32.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 32.5 Beat 5

INFO undersize notes speak only if the preface remains a final chunk. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-32.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 33. Scenario book: two resource sections

### 33.1 Beat 1

Section A uses heading cuts. Section B uses numbered-list cuts. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-33.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 33.2 Beat 2

Each section keeps its own pack budget unless the CLI overrides both. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-33.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 33.3 Beat 3

Chunks carry section_name from their origin table. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-33.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 33.4 Beat 4

Activity lists both sections. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-33.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 33.5 Beat 5

Output schemas can include CHUNK_SECTION_NAME. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-33.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 34. Scenario book: include and exclude

### 34.1 Beat 1

Exclude matching 'DEPRECATED' marks those pieces invalid. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-34.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 34.2 Beat 2

Include matching '^## ' would keep only heading-led pieces if used alone. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-34.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 34.3 Beat 3

Exclude still wins when both would match. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-34.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 34.4 Beat 4

Invalid pieces are not sent as the answered material. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-34.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 34.5 Beat 5

Packing will not glue a valid piece to an invalid neighbour. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-34.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 35. Scenario book: live retry

### 35.1 Beat 1

A local gateway returns 502 on the first attempt. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-35.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 35.2 Beat 2

retry_delay waits, then doubles. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-35.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 35.3 Beat 3

max_retry bounds the attempt count. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-35.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 35.4 Beat 4

A 504 ends the attempt class that is terminal. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-35.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 35.5 Beat 5

Stdout still does not receive a spinner. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-35.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 36. Scenario book: exclusive directory write

### 36.1 Beat 1

A first live run writes session files through staging and commits. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-36.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 36.2 Beat 2

A second run in mode x hits existing names. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-36.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 36.3 Beat 3

The error points at the staging directory for salvage. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-36.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 36.4 Beat 4

Mode w would overwrite instead. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-36.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 36.5 Beat 5

Mode a would append. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-36.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 37. Scenario book: stdin pipe

### 37.1 Beat 1

curl writes HTML or Markdown to stdout. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-37.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 37.2 Beat 2

The prompt contains {STDIN}. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-37.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 37.3 Beat 3

dragiter interpolates the pipe contents once per assembled session as the template specifies. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-37.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 37.4 Beat 4

Simulation still prints a board, not the model. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-37.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 37.5 Beat 5

No second hidden stdin injection occurs if the placeholder is absent, except the documented -t path. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-37.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 38. Scenario book: JSONL loop

### 38.1 Beat 1

Each line is an object with keys for audience and product. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-38.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 38.2 Beat 2

Those keys appear as placeholders. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-38.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 38.3 Beat 3

Session count multiplies by the line count. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-38.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 38.4 Beat 4

The board loop item count matches the line count. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-38.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 38.5 Beat 5

A malformed line fails the loop builder rather than skipping silently if that is the builder's contract; operators treat loop files as data. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-38.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 39. Scenario book: context pressure

### 39.1 Beat 1

chars_per_token, max_context_tokens and max_output_tokens are all set. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-39.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 39.2 Beat 2

The estimator writes per-session figures to the activity file. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-39.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 39.3 Beat 3

The board shows peak / limit and window yes or no. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-39.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 39.4 Beat 4

Those warnings are not mixed into small / over. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-39.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 39.5 Beat 5

Missing settings show n/a and -- rather than invented integers. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-39.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 40. Scenario book: mTLS and custom CA

### 40.1 Beat 1

A private gateway requires a client certificate. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-40.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 40.2 Beat 2

The operator sets the PEM paths through flags or environment. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-40.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 40.3 Beat 3

A custom CA bundle replaces the default trust store for that run. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-40.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 40.4 Beat 4

TCP keep-alive is available if the transport needs it. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-40.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 40.5 Beat 5

None of these settings alter chunking arithmetic. This beat belongs to the scenario book so that a `###` overflow cut yields a measurable extra piece while remaining about dragiter.

Operators repeating this beat should keep simulate on until the board matches their expectation. Live calls are out of scope for proving regex_patterns. Files written with `-O` in simulate mode contain session boards, not provider prose. The activity file, if requested, records the resource section's regex_patterns list only.

#### REQ-X-40.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 41. Design rationale kept beside the requirements

### 41.1 Pipeline over framework

dragiter is a pipeline of workers, not a plugin host. Adding a vector store would be a different product. The requirement profile therefore spends its pages on chunking arithmetic rather than an ecosystem pitch.

#### REQ-X-41.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 41.2 Files over databases

Prompts, resources and loops are files so they can be reviewed in Git. That choice is why TOML and JSONL appear instead of a project database.

#### REQ-X-41.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 41.3 Boards over dashboards

A four-column Markdown table fits a terminal and a pull request. A web dashboard would contradict the Unix claim.

#### REQ-X-41.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 41.4 Hard errors over guesswork

The removed singular key fails loudly. The 200-chunk cap fails loudly. Exclusive writes fail loudly. The profile prefers those failures to quiet corruption.

#### REQ-X-41.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 41.5 Counts over dumps

Debug exists to count cuts. It would be easier to print every piece. That would leak material into logs and drown the signal.

#### REQ-X-41.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 41.6 British English over mixed locale

Product text stays in British English so operators are not reading two dialects in one tree. User-facing UI copy would follow a different rule only if an application locale were introduced; there is no GUI.

#### REQ-X-41.6 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 41.7 Streaming over batch-response clients

Local models can talk for minutes. Streaming plus an INFO heartbeat is the honesty mechanism. A blocking non-stream call would look dead.

#### REQ-X-41.7 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 41.8 Staging over in-place writes

Directory output stages first because a mid-run name collision should not discard completed model text.

#### REQ-X-41.8 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 41.9 Origins over last-write-wins maps

Settings remember where they came from. That is why a default cannot stomp a CLI flag later in the process.

#### REQ-X-41.9 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 41.10 Two greedy packs over one

Heading splits create awkward edges. Computing both directions is cheap compared with a general bin-packing solver, which the product does not include.

#### REQ-X-41.10 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 42. Field dictionary for operators

### 42.1 Field `glob_patterns`

**Type.** list of strings  **Meaning.** Candidate file selection relative to the section root, or absolute as an escape hatch.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.2 Field `base_directory`

**Type.** optional path  **Meaning.** Section search root. Relative values rebase onto -b. Absolute values do not.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.3 Field `regex_patterns`

**Type.** list of strings  **Meaning.** Staged split. Index 0 always. Later indices overflow only.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.4 Field `regex_pattern`

**Type.** removed  **Meaning.** Presence aborts collection.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.5 Field `include_filters`

**Type.** list of strings  **Meaning.** Permission after exclusion.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.6 Field `exclude_filters`

**Type.** list of strings  **Meaning.** Veto, case-insensitive multiline search.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.6 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.7 Field `pack_limit_chars`

**Type.** optional int  **Meaning.** Section budget. Overridden by a global value including 0.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.7 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.8 Field `section name`

**Type.** TOML table name  **Meaning.** Must be non-empty. Copied onto every chunk.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.8 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.9 Field `CHUNK_NUM_ID`

**Type.** int  **Meaning.** Running identifier for filename schemas.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.9 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.10 Field `CHUNK_SECTION_NUM_ID`

**Type.** int  **Meaning.** Per-section identifier.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.10 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.11 Field `CHUNK_FILE_NAME`

**Type.** sanitised string  **Meaning.** Safe interpolation token.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.11 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.12 Field `CHUNK_SECTION_NAME`

**Type.** sanitised string  **Meaning.** Safe interpolation token.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.12 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.13 Field `LOOP_NUM_ID`

**Type.** int  **Meaning.** Loop ordinal coerced for format specifiers.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.13 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.14 Field `LOOP_ID / LOOP_CONTENT`

**Type.** string  **Meaning.** Display and schema text for the loop line.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.14 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.15 Field `TIMESTAMP`

**Type.** string  **Meaning.** UTC sortable stamp with nanosecond padding.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.15 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.16 Field `STDIN`

**Type.** string  **Meaning.** Piped standard input when the template asks for it.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.16 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.17 Field `output mode x`

**Type.** enum  **Meaning.** Exclusive create, default.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.17 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.18 Field `output mode w`

**Type.** enum  **Meaning.** Overwrite.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.18 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.19 Field `output mode a`

**Type.** enum  **Meaning.** Append.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.19 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.20 Field `simulate`

**Type.** bool  **Meaning.** No live completions.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.20 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.21 Field `verbose`

**Type.** bool  **Meaning.** INFO logging.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.21 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.22 Field `debug`

**Type.** bool  **Meaning.** DEBUG logging.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.22 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.23 Field `sequential_processing`

**Type.** bool  **Meaning.** One session per chunk.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.23 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.24 Field `chars_per_token`

**Type.** float  **Meaning.** Heuristic only.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.24 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.25 Field `max_context_tokens`

**Type.** int  **Meaning.** Window size.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.25 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.26 Field `max_output_tokens`

**Type.** int  **Meaning.** Reserved generation budget.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.26 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.27 Field `retry_delay`

**Type.** int  **Meaning.** Base seconds, range 0–20, default 3 when unset at runtime.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.27 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.28 Field `max_retry`

**Type.** int  **Meaning.** Attempts, range 0–9.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.28 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.29 Field `base_url`

**Type.** URL  **Meaning.** OpenAI-compatible root.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.29 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.30 Field `model_name`

**Type.** string  **Meaning.** Provider identifier.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.30 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.31 Field `api_key`

**Type.** secret  **Meaning.** Masked in activity logs.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.31 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.32 Field `temperature`

**Type.** float  **Meaning.** Sampling; examples often use 0.0.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.32 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.33 Field `ca_bundle_file`

**Type.** path  **Meaning.** Optional PEM trust store.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.33 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.34 Field `client_cert_file`

**Type.** path  **Meaning.** Optional mTLS certificate.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.34 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.35 Field `client_key_file`

**Type.** path  **Meaning.** Optional mTLS key.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.35 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.36 Field `tcp_keep_alive`

**Type.** bool  **Meaning.** httpx2 transport option.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.36 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.37 Field `activity file`

**Type.** JSONL path  **Meaning.** Written only when requested.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.37 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.38 Field `log file`

**Type.** text path  **Meaning.** Append-only, no rotation.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.38 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.39 Field `output delimiter`

**Type.** string  **Meaning.** Joiner for concatenated results.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.39 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 42.40 Field `output filename schema`

**Type.** string  **Meaning.** Directory naming template.  The staged-regex example may interpolate or display this field but must not invent a second spelling.

#### REQ-X-42.40 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 43. Operator runbooks

### 43.1 Dry-run runbook

From the example directory, invoke dragiter with `-s -p` and `-r` pointing at the staged-regex files. Read the board. Confirm pack and small/over before any live flag is introduced.

#### REQ-X-43.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 43.2 Overflow runbook

Edit only pack_limit_chars and the second regex. Re-run with `-s -d`. Search the log for 'pattern 2/'. Do not change the prompt while measuring chunk arithmetic.

#### REQ-X-43.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 43.3 Override runbook

Leave the section budget at 4000. Pass `--pack-limit-chars 0`. Confirm overflow silence. Then pass `--pack-limit-chars 4000` and confirm overflow returns even if the section value differs.

#### REQ-X-43.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 43.4 Filter runbook

Add an exclude filter that cannot match this profile, such as a token that does not occur. Chunk counts must stay put. Then add a real token from the glossary and watch invalid counts rise in DEBUG.

#### REQ-X-43.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 43.5 Output runbook

Write `-O` into an empty directory with mode x. Confirm one file per session in simulate mode. Repeat and expect exclusive failures plus a staging path in the error.

#### REQ-X-43.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 43.6 Activity runbook

Add `-a` and confirm the resources record lists regex_patterns as a list and does not list regex_pattern. Confirm api_key is masked if settings are logged.

#### REQ-X-43.6 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 43.7 Interrupt runbook

A KeyboardInterrupt during a live stream should end with status 130. Simulation is the wrong place to practise this; mention it only so the profile stays complete.

#### REQ-X-43.7 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 44. Mapping profile chapters to code units

### 44.1 ResourceCollector

Owns globbing, containment, encoding checks, and rejection of the removed singular key. Profile chapters 4, 14 and 24 trace here.

#### REQ-X-44.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 44.2 MaterialTokenizer

Owns compile, staged split, refine, filter, pack, circuit breaker, INFO size notes and DEBUG traces. Chapters 5, 17 and 26 trace here.

#### REQ-X-44.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 44.3 OutputWriter and simulation_brief

Own boards, file routing, staging and small/over display. Chapters 8, 10 and 13 trace here.

#### REQ-X-44.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 44.4 LoggingConfigurator

Owns the WARNING / INFO / DEBUG mapping from flags. Chapter 13 traces here.

#### REQ-X-44.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 44.5 Chat path

Owns simulate versus stream, retries and usage. Chapters 8 and 12 trace here.

#### REQ-X-44.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 44.6 Settings models

Own origins and rebase rules. Chapter 11 traces here.

#### REQ-X-44.6 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 44.7 Activity providers

Own JSONL record shapes. Chapter 13 traces here.

#### REQ-X-44.7 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 44.8 Example tree

Owns the public demonstration. Chapter 25 traces here. Example 04 will live beside this file.

#### REQ-X-44.8 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.


---

## 45. Residual risks for example 04

### 45.1 Heading edits break patterns

If a future editor demotes chapters from ## to bold text, the sample patterns stop cutting. That is a documentation risk, not a code risk.

#### REQ-X-45.1 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 45.2 Board pack column versus section budget

Operators may misread pack off as 'no packing happened' when only the CLI budget is unset. The README must spell out the distinction.

#### REQ-X-45.2 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 45.3 Very small leftover headings

A heading-only piece after strip can be under 50 characters and raise small. That is correct.

#### REQ-X-45.3 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 45.4 Locale of this file

The profile is British English. German conversation about it must not leak into the sample files.

#### REQ-X-45.4 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

### 45.5 Licence of the example text

This profile is part of the dragiter examples and follows the same AGPL-3.0-or-later project licensing as the surrounding tree.

#### REQ-X-45.5 — Acceptance slice

**Statement.** The behaviour described in this section shall match the shipped dragiter pipeline for the same topic.

**Rationale.** The staged-regex example is only useful if each overflow piece still carries a testable claim rather than empty filler.

**Acceptance criteria.**

1. A simulate run that exercises this topic does not contradict the section text.

2. Debug traces, when enabled, remain free of payload dumps.

3. Documentation extracted by `dragiter-gen-docs` remains the court of appeal.

---

## 46. Extended acceptance scripts in prose

### 46.1 Script step 1

Perform simulate run variant 1 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 1 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-01 — Variant 1 remains heading-based

**Statement.** Script step 1 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.2 Script step 2

Perform simulate run variant 2 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 2 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-02 — Variant 2 remains heading-based

**Statement.** Script step 2 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.3 Script step 3

Perform simulate run variant 3 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 3 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-03 — Variant 3 remains heading-based

**Statement.** Script step 3 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.4 Script step 4

Perform simulate run variant 4 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 4 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-04 — Variant 4 remains heading-based

**Statement.** Script step 4 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.5 Script step 5

Perform simulate run variant 5 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 5 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-05 — Variant 5 remains heading-based

**Statement.** Script step 5 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.6 Script step 6

Perform simulate run variant 6 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 6 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-06 — Variant 6 remains heading-based

**Statement.** Script step 6 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.7 Script step 7

Perform simulate run variant 7 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 7 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-07 — Variant 7 remains heading-based

**Statement.** Script step 7 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.8 Script step 8

Perform simulate run variant 8 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 8 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-08 — Variant 8 remains heading-based

**Statement.** Script step 8 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.9 Script step 9

Perform simulate run variant 9 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 9 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-09 — Variant 9 remains heading-based

**Statement.** Script step 9 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.10 Script step 10

Perform simulate run variant 10 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 10 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-10 — Variant 10 remains heading-based

**Statement.** Script step 10 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.11 Script step 11

Perform simulate run variant 11 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 11 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-11 — Variant 11 remains heading-based

**Statement.** Script step 11 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.12 Script step 12

Perform simulate run variant 12 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 12 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-12 — Variant 12 remains heading-based

**Statement.** Script step 12 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.13 Script step 13

Perform simulate run variant 13 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 13 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-13 — Variant 13 remains heading-based

**Statement.** Script step 13 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.14 Script step 14

Perform simulate run variant 14 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 14 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-14 — Variant 14 remains heading-based

**Statement.** Script step 14 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.15 Script step 15

Perform simulate run variant 15 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 15 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-15 — Variant 15 remains heading-based

**Statement.** Script step 15 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.16 Script step 16

Perform simulate run variant 16 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 16 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-16 — Variant 16 remains heading-based

**Statement.** Script step 16 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.17 Script step 17

Perform simulate run variant 17 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 17 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-17 — Variant 17 remains heading-based

**Statement.** Script step 17 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.18 Script step 18

Perform simulate run variant 18 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 18 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-18 — Variant 18 remains heading-based

**Statement.** Script step 18 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.19 Script step 19

Perform simulate run variant 19 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 19 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-19 — Variant 19 remains heading-based

**Statement.** Script step 19 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.

### 46.20 Script step 20

Perform simulate run variant 20 against this profile. Keep the prompt constant. Change only the resource patterns or the pack budget. Write down chunks, valid chunks, small and over. Compare with the previous variant. A change that cannot be explained by the staged-split contract is a defect in the example or in the tokenizer.

**Expected discipline.** No live endpoint is required. No payload is copied into the notes. Pattern indices in DEBUG, when used, are the evidence that overflow ran. Variant 20 still uses heading anchors `##` and `###` rather than per-line cuts, so the 200-chunk cap stays out of the happy path.

#### REQ-SCR-20 — Variant 20 remains heading-based

**Statement.** Script step 20 shall not switch the official example to a line-splitting pattern.

**Rationale.** Line splitting would demonstrate the circuit breaker, which is a different example.

**Acceptance criteria.**

1. Official sample patterns stay `^##\s+` then `^###\s+`.

2. The board remains the primary numeric record.


---

## 47. Glossary expansions for overflow cuts

### 47.1 Term — Chunk

Chunk: Final piece after split, filter and pack. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-01 — Stable sense of Chunk

**Statement.** Writers of the example README shall use *chunk* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *chunk* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.2 Term — Piece

Piece: Intermediate text span after a regex cut, before pack. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-02 — Stable sense of Piece

**Statement.** Writers of the example README shall use *piece* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *piece* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.3 Term — Section table

Section table: A TOML table in the resource file. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-03 — Stable sense of Section table

**Statement.** Writers of the example README shall use *section table* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *section table* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.4 Term — Section heading

Section heading: A `###` title in this profile. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-04 — Stable sense of Section heading

**Statement.** Writers of the example README shall use *section heading* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *section heading* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.5 Term — Chapter heading

Chapter heading: A `##` title in this profile. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-05 — Stable sense of Chapter heading

**Statement.** Writers of the example README shall use *chapter heading* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *chapter heading* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.6 Term — Budget

Budget: pack_limit_chars effective value. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-06 — Stable sense of Budget

**Statement.** Writers of the example README shall use *budget* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *budget* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.7 Term — Origin

Origin: CLI, config, environment or default. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-07 — Stable sense of Origin

**Statement.** Writers of the example README shall use *origin* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *origin* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.8 Term — Board

Board: Simulate run table. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-08 — Stable sense of Board

**Statement.** Writers of the example README shall use *board* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *board* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.9 Term — Trace

Trace: DEBUG log line with counts. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-09 — Stable sense of Trace

**Statement.** Writers of the example README shall use *trace* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *trace* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.10 Term — Note

Note: INFO size message. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-10 — Stable sense of Note

**Statement.** Writers of the example README shall use *note* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *note* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.11 Term — Veto

Veto: Exclude filter match. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-11 — Stable sense of Veto

**Statement.** Writers of the example README shall use *veto* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *veto* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.12 Term — Permission

Permission: Include filter match. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-12 — Stable sense of Permission

**Statement.** Writers of the example README shall use *permission* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *permission* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.13 Term — Staging

Staging: Hidden directory used before commit. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-13 — Stable sense of Staging

**Statement.** Writers of the example README shall use *staging* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *staging* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.14 Term — Masking

Masking: Replacement of secret-like activity fields. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-14 — Stable sense of Masking

**Statement.** Writers of the example README shall use *masking* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *masking* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.15 Term — Heartbeat

Heartbeat: Ten-second INFO while streaming. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-15 — Stable sense of Heartbeat

**Statement.** Writers of the example README shall use *heartbeat* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *heartbeat* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.16 Term — Attempt

Attempt: One live completion try, counted by max_retry. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-16 — Stable sense of Attempt

**Statement.** Writers of the example README shall use *attempt* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *attempt* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.17 Term — Window

Window: Estimated context occupancy. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-17 — Stable sense of Window

**Statement.** Writers of the example README shall use *window* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *window* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.18 Term — Placeholder

Placeholder: Brace token in templates or filenames. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-18 — Stable sense of Placeholder

**Statement.** Writers of the example README shall use *placeholder* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *placeholder* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.19 Term — Sanitise

Sanitise: Make a token safe for a filename. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-19 — Stable sense of Sanitise

**Statement.** Writers of the example README shall use *sanitise* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *sanitise* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.

### 47.20 Term — Containment

Containment: Refuse paths outside a root. In the staged-regex example this term must be used with that meaning so that README arithmetic stays unambiguous.

#### REQ-GLOSS-20 — Stable sense of Containment

**Statement.** Writers of the example README shall use *containment* as defined here.

**Rationale.** Overloaded words hide whether packing or splitting changed a number.

**Acceptance criteria.**

1. The README does not use *containment* for a different artefact.

2. This definition remains consistent with chapters 5 and 19.


---

## 48. Document statistics for the example authors

### 48.1 Why the length exists

A short specification cannot demonstrate overflow. Chapter 5 and the later books exist so that `pack_limit_chars = 4000` is smaller than several `##` pieces. The length is an instrument.

### 48.2 Heading inventory

Authors should count `##` and `###` lines in this file after edits. Those counts are the theoretical maxima for the two patterns before packing. They are not the expected final chunk counts.

### 48.3 Editing rule

Do not flatten headings to emphasise text. Emphasis is not a cut point in the sample resource file.

### 48.4 Encoding

The file is UTF-8. The collector's encoding detector must accept it. No byte-order mark is required.

