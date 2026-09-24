# Requirements Profile: Staging Workspace and Commit

| Field | Value |
|---|---|
| Document | `design/specs/spec-stag-staging.md` (formerly `dragiter_ap_staging_v2.md`) |
| Code | `STAG` |
| Type | technical |
| Serves | `OUTP` |
| Product | dragiter |
| Version | 2.2 (supersedes v2.1, v2.0 and `dragiter_ap_staging.md`, v1.0) |
| Status | agreed target state (specification) |
| Date | 2026-09-24 |
| Read pin | `eb8097bcdbfd826777b06434fb9b39d11598916a` |
| Staging commit (baseline) | `534b2cd9faa75aadee5a0b993d52f4dd82a7d6c6` |
| Language | English throughout |
| Form | Contract for spec-driven development, not an implementation |

This profile does not replace the source code. **This target state** governs all future work; the implementation is built against it, not adapted from the current mechanics. Read pin and staging commit only mark the baseline the implementation starts from.

---

## Change history vs. v2.1

- **Editorial only, no normative change.** Acceptance criteria carry stable identifiers `STAG-01` to `STAG-36` (Section 10); the former numbers map one to one. Identifiers are never renumbered or reused. File moved to `design/specs/spec-stag-staging.md`.

## Change history vs. v2.0

- **Section 4 (drift) removed.** The profile no longer documents current behaviour; implementation follows the target state alone. The section number is kept reserved.

## Change history vs. v1.0

- **Workspace location stays local.** The proposal to move `-o`/`-O` workspaces into system temp was evaluated and rejected (same-FS-rename argument, Sections 5.3/11 unchanged).
- **Persist model unified.** Instead of sink-specific persist logic (`-O`: many finished files, `-o`/stdout: one continuously extended file), Persist now writes an identical, small, finished **shard** file per completion for all three sinks (Section 6, new).
- **New "Assembly" step** before commit for `-o` and stdout-only: shards are merged there into a single file (Section 7.0, new).
- **New term "Shard"** added to the glossary (Section 3).
- **`{TIMESTAMP}` origin clarified:** the persist timestamp of an `-O` shard is that file's filesystem mtime, no separate metadata sidecar (Section 6.3, new).
- **`-o` and `-O` are now mutually exclusive.** Never both active at once. If neither is given, the stream goes to standard out.
- **`-m a` (append) precisely specified:** target missing **or** empty (0 bytes) → no leading delimiter; target non-empty → leading delimiter. A delimiter never appears at the end of a file.
- Section 7.7 (collision `-o`/`-O`) and Phase D of the validation plan are removed entirely as a consequence of mutual exclusivity — see "Removed sections" below.

---

## 1. Purpose

Every successful completion must immediately exist as a finished shard file in a run workspace. After the last completion, `OutputWriter` transfers the shards to the active sink — for `-O` by direct rename per shard, for `-o`/stdout-only via a preceding Assembly step that merges the shards into one file. A transfer error aborts immediately and leaves the affected workspace in place, so that expensive replies are not lost.

Same-FS rename applies to `-O` and `-o`: the workspace is a child of the target parent.
stdout-only has no file target; its workspace lives in the **user's default temp directory**.

`-o` and `-O` are **mutually exclusive** — never both active in the same run. If neither flag is given, the run is stdout-only.

Not a purpose: OS temp as the parent of `-o`/`-O`, a shared workspace for multiple sinks, a second scratch model (`.dragiter-partial/`, `.tmp_staging_file_*` as a *file*), a metadata sidecar for shard timestamps, combined `-o`+`-O` operation.

---

## 2. Scope and boundaries

### 2.1 In scope

- Live run with a prompt (workspace is created).
- Sinks `-O DIR`, `-o FILE`, and stdout-only (neither `-o` nor `-O`). `-o` and `-O` are mutually exclusive.
- `output_mode` (`-m x|w|a`) only for `-o`/`-O`.
- `output_delimiter`, `output_filename_schema`, the `{TIMESTAMP}` token.
- Early check before the first completion, where names are determinable without a write timestamp.
- Shard persist (identical across all three sinks) and Assembly (`-o`/stdout-only only).

### 2.2 Out of scope

- Packing staging, resource collection, simulate boards as content.
- Implementation shape (module boundaries, function names beyond the contracts named here). Implementation decisions belong in a separate design-notes document (see `dragiter_design_notes.md`).
- Cleaning up foreign PIDs.
- Shell redirection of stdout (`>`, `>>`, `|`) as a file sink.

### 2.3 Deliberately unchanged

- Early `-m x` and intra-run duplicate-name checks before the chats, when the schema does **not** contain `{TIMESTAMP}`.
- `{TIMESTAMP}` in the schema skips this pre-check.
- PID isolates workspaces; cleanup only touches the run's own workspace.
- stdout echo only when neither `-o` nor `-O` is set.

---

## 3. Terms

| Term | Meaning |
|---|---|
| Sink | `-O DIR`, `-o FILE`, or stdout-only. Exactly one is active per run. |
| Parent | Directory that hosts the workspace |
| User temp | User's default temp directory: `$TMPDIR` if set and usable, otherwise the platform default (`tempfile.gettempdir()` / `/tmp` on Unix). Not CWD, not `$XDG_CACHE_HOME`, not `$XDG_RUNTIME_DIR` |
| Workspace | Hidden child of the parent, scoped to this run and this sink only |
| Persist | Writing a **finished** shard file into the workspace after a completion |
| Shard | Finished single-completion file in the workspace, named by a run-local, sequential number (`res<N>`, fixed width). No relation to the final name, schema, or `FILE.name` |
| Assembly | `-o`/stdout-only only: merging all shards of a workspace into one file, immediately before its commit |
| Commit | Transferring workspace → sink via `OutputWriter`, after Persist (and, for `-o`/stdout, after Assembly) |
| Rename | Same-FS `rename`/`replace` of a shard or assembly file onto the final path (`-o`/`-O`) |
| Slot | A planned session under `-O` |
| Empty | Content with no visible characters after strip |

---

## 4. Reserved — removed in v2.1

This section described the drift between the code at the read pin and the target state. It is removed: implementation follows this target state alone and is not derived from the current mechanics. The number is kept reserved rather than reused, to avoid renumbering downstream references.

---

## 5. Location contract

### 5.1 Parent

- `-O DIR`: parent is `DIR`. `DIR` must exist, be a directory, and be writable before the first completion. dragiter does not create `DIR`.
- `-o FILE`: parent is `FILE.parent`, with the same existence and writability rule.
- stdout-only: parent is **user temp**. The directory must exist and be writable. If it is missing or unusable, abort before the first completion.
- Relative paths for `-o`/`-O` are resolved against the process CWD at the time of validation.

### 5.2 Workspace paths

| Sink | Workspace |
|---|---|
| `-O DIR` | `DIR/.tmp_staging_dir_<PID>/` |
| `-o FILE` | `FILE.parent/.tmp_staging_file_<PID>/` |
| stdout-only | `{user temp}/.tmp_staging_stdout_<PID>/` |

Three prefixes, even if `FILE.parent == DIR` or CWD = user temp by coincidence. No shared workspace.

`-o`/`-O` never create anything under user temp. stdout-only never creates anything in CWD or next to `-o`/`-O`.

### 5.3 Same-FS

`-o`/`-O`: the workspace child sits on the target parent's filesystem; rename is the normal case for `x`/`w`. Because the workspace is already a child of the target parent, the Assembly result (for `-o`) is automatically same-FS to the target too — no extra buffer path needed.
stdout-only: no file target, no rename; same-FS is irrelevant. User temp is correct here.

---

## 6. Persist contract (unified)

The workspace is created after successful validation and after the early check passes, **before** the sink's first completion is persisted.

Persist is **identical** across all three sinks: every completion — including an empty one (`∅`) — immediately produces exactly one finished shard file in the workspace as soon as it completes. At this step the chat manager knows nothing about sink-specific logic (delimiter, filtering of empty replies, final name, `output_filename_schema`) — only "completion finished → write a shard". All sink-specific decisions are made at commit (`-O`: Sections 7.1–7.3; `-o`/stdout: Assembly, Section 7.0).

### 6.1 Shard naming scheme

- Format `res<N>`, `N` numeric, zero-padded, at least 6 digits (up to 999,999 completions per run and sink).
- Sequential starting at `1`, strictly workspace-local — no counter shared across sinks or runs.
- A digit-count overflow is an error case (immediate abort with a message), never silent behaviour and never automatic width expansion.
- The shard name has no relation to `output_filename_schema`, `FILE.name`, or `stdout.txt` — those are final names only (Sections 7.5–7.6).

### 6.2 Shard content

- A shard contains exactly the text of its completion, unchanged, without `output_delimiter`, without concatenation with other shards.
- An empty completion produces an empty shard (0-byte content) — never a missing shard. Whether an empty shard remains visible in the final artefact (`-O`, T1a) or is discarded (`-o`/stdout) is decided exclusively at commit/Assembly.

### 6.3 Timestamp for `{TIMESTAMP}` (`-O` only)

- A shard's persist timestamp is its filesystem mtime at the time of writing. No separate metadata sidecar.
- If `output_filename_schema` contains `{TIMESTAMP}`, the commit uses exactly that shard's mtime — no new clock read at rename time.
- Without `{TIMESTAMP}` in the schema, the shard mtime is not needed; the final name is known before the chats (early check, Section 8).

---

## 7. Commit contract

Commit begins only once all of the sink's completions are persisted (or the run has already aborted due to a persist/chat error — in which case there is no commit).

`-o` and `-O` are mutually exclusive, so there is never an ordering question between them.
If stdout-only is active, there is no file sink and no `-m` commit.

### 7.0 Assembly (`-o` and stdout-only only)

Before this sink's commit:

1. Read all shards of the workspace in ascending sequence order (`res000001`, `res000002`, …).
2. Discard empty shards (0 bytes).
3. Merge the remaining shards into one content: the first non-empty shard without a leading `output_delimiter`, every further shard preceded by exactly one `output_delimiter`.
4. Write the result as `FILE.name` (for `-o`) or `stdout.txt` (for stdout-only) into the same workspace. This is automatically same-FS to the target (Section 5.3).
5. Shards remain in place after Assembly; they are removed only together with the rest of the workspace when the subsequent commit succeeds (Section 7.4 or 7.9).
6. No non-empty shard present: `FILE.name`/`stdout.txt` is **not** created (matches 6.2/7.8).

From here, Sections 7.1–7.3 (file sinks) or 7.9 (stdout) apply unchanged — the `FILE.name`/`stdout.txt` produced by Assembly is treated exactly as before.

`-O` never goes through Assembly: its shards are already the finished final contents and are moved directly per 7.1–7.3.

### 7.1 `-m x`

1. Preflight all final paths of this sink.
2. At least one exists: no rename, sink state unchanged, workspace remains, run aborts.
3. None exist: only rename the shard(s) or the Assembly result onto the final paths.
4. First rename failure: stop immediately, no further file of this sink, workspace remains. Already-successful renames of this sink are not rolled back.

### 7.2 `-m w`

- No existence preflight.
- Each target file is created or overwritten via rename/`replace`.
- First failure: stop immediately, workspace remains, already-replaced targets remain.

### 7.3 `-m a`

- No rename.
- Copy: target missing or empty (0 bytes) → new block is written without a leading delimiter. Target non-empty → `output_delimiter` + new block is appended.
- New block itself empty: target is left completely untouched, regardless of target state.
- A delimiter never appears at the end of a file — it only ever joins existing content with new, non-empty content.
- First failure: stop immediately, workspace remains.

### 7.4 Success (file sinks)

After a sink's commit completes fully, **only** that sink's own workspace (including any remaining shards) is removed.

### 7.5 `-O` final names

`output_filename_schema` plus session data. `{TIMESTAMP}` = the persist timestamp (mtime) of the corresponding shard (Section 6.3).

### 7.6 `-o` final name

Always `FILE`. The schema does not apply to the `-o` filename.

### 7.7 Reserved — removed in v2.0

This section covered the interaction of both file sinks being active simultaneously. It no longer applies: `-o` and `-O` are mutually exclusive (Section 1). The number is kept reserved rather than reused, to avoid renumbering downstream references.

### 7.8 `-o`-only replies, all empty

Do not create or modify `FILE`. Matches 7.0, point 6: Assembly creates no file when no non-empty shard exists.

### 7.9 stdout-only

- Assembly (7.0) first produces `stdout.txt` in the workspace.
- Commit reads the workspace file `stdout.txt` and writes its content to stdout.
- `-m` is not applied.
- Shell redirection does not change the sink; the workspace stays in user temp.
- Success: the stdout workspace (including shards) is gone.
- Error while reading or writing stdout: stop immediately, workspace remains.
- No content file (only empty shards, Assembly produces no `stdout.txt`): nothing from the replies goes to stdout, workspace is gone.

---

## 8. Early check (before the first completion)

Applies when final names are determinable without a write timestamp (schema **without** `{TIMESTAMP}`).

| Case | Behaviour |
|---|---|
| `-m x` and `-o FILE` exists | Abort, no workspace, no chats |
| `-m x` and the planned `-O` name exists | Abort, no workspace, no chats |
| Two sessions, same planned `-O` name | Abort before the chats, no workspace (4a) |
| Schema contains `{TIMESTAMP}` | No early check on these names; the only x-lock is the commit preflight |
| stdout-only | No file target, no early check on names |

---

## 9. Error message

On commit or preflight abort, the message must include:

- the failed target path (on multiple preflight hits, the list of colliding paths); for stdout-only, a note that the sink is stdout;
- the workspace path of the affected sink.

No requirement to enumerate files already moved successfully.

---

## 10. Acceptance criteria

Normative, testable. Given / when / then.

Each criterion carries a stable identifier `STAG-NN`. Identifiers are assigned once, in sequence, and are never renumbered or reused; a new criterion takes the next free number and is placed where it belongs in the text. A withdrawn criterion stays listed, marked *withdrawn*, so that its identifier remains taken.

### Location and creation

- **STAG-01** Given `-O DIR` and `DIR` does not exist or is not a directory, when the run starts, then abort before the first completion and no workspace.
- **STAG-02** Given `-O DIR` writable, when the first completion is persisted, then only under `DIR/.tmp_staging_dir_<PID>/`.
- **STAG-03** Given `-o FILE` and `FILE.parent` is missing or not writable, when the run starts, then abort before the first completion and no workspace.
- **STAG-04** Given only `-o FILE`, when persisting, then only under `FILE.parent/.tmp_staging_file_<PID>/`, never under `.tmp_staging_dir_*`, and never under user temp as the chosen parent.
- **STAG-05** Given only `-O DIR`, when persisting, then no `.tmp_staging_file_*` and no `.tmp_staging_stdout_*` is created.
- **STAG-06** Given both `-o` and `-O` on the command line at once, when the run starts, then abort immediately with an error message, before any workspace is created or path validated.

### Persist (shards, all sinks)

- **STAG-07** Given a non-empty completion under any sink, when it is persisted, then a new shard `res<N>` is created in the corresponding workspace with exactly its text, no delimiter.
- **STAG-08** Given an empty completion under any sink, when it is persisted, then a shard `res<N>` is still created, with 0-byte content.
- **STAG-09** Given two consecutive completions of the same sink, when both are persisted, then the second shard's sequence number is exactly one greater than the first's.
- **STAG-10** Given an `-O` shard, when it is written, then its filesystem mtime is the timestamp later used for `{TIMESTAMP}` (if the schema contains it).

### Assembly (`-o`/stdout-only)

- **STAG-11** Given `-o` and at least one non-empty shard, when the commit begins, then after Assembly `FILE.name` exists in the workspace, starting with the first non-empty shard's text without a leading `output_delimiter`.
- **STAG-12** Given `-o` and multiple non-empty shards, when Assembly runs, then they are joined in sequence order by exactly one `output_delimiter`.
- **STAG-13** Given `-o` and only empty shards, when Assembly runs, then `FILE.name` is not created in the workspace.
- **STAG-14** Given stdout-only, when Assembly runs, then STAG-11 to STAG-13 apply analogously to `stdout.txt`.
- **STAG-15** Given a successful Assembly, when the subsequent commit has not yet completed, then the individual shards remain in the workspace in addition to the Assembly result.

### Persist and commit, `-O` empty

- **STAG-16** Given `-O` and an empty completion, when the commit succeeds, then the schema file exists in `DIR` and is empty (from the empty shard).
- **STAG-17** Given `-O -m a` and empty new content, when committing, then the target file does not change.

### Commit `-O`

- **STAG-18** Given all `-O` shards finished and `-m x`, when no schema path exists in `DIR`, then the shards are moved to `DIR` and the `-O` workspace is gone afterwards.
- **STAG-19** Given the same shards and `-m x`, when at least one schema path exists, then no move happens, `DIR` is unchanged, the `-O` workspace remains, message per Section 9.
- **STAG-20** Given `-m w` under `-O`, when all renames succeed, then the schema files in `DIR` are replaced or created and the `-O` workspace is gone.
- **STAG-21** Given a rename under `-O` (`x` or `w`), when one fails, then stop immediately, no further move for this sink, workspace remains, already-moved shards remain in `DIR`.

### Commit `-o`

- **STAG-22** Given a finished Assembly result `FILE.name` and `-m x` and `FILE` is missing, when committing, then rename onto `FILE`, `-o` workspace gone.
- **STAG-23** Given the same Assembly result and `-m x` and `FILE` exists, when committing, then no rename, `FILE` unchanged, `-o` workspace remains, message with `FILE` and workspace path.
- **STAG-24** Given the same Assembly result and `-m w`, when committing, then replace of `FILE`, `-o` workspace gone.
- **STAG-25** Given the same Assembly result and `-m a`, when committing, then append (or creation without a leading delimiter, per Section 7.3), `-o` workspace gone after success.

### `{TIMESTAMP}`

- **STAG-26** Given `{TIMESTAMP}` in the schema, when the final file is created, then it contains the mtime timestamp of the corresponding `-O` shard, not a new commit-time timestamp.
- **STAG-27** Given `{TIMESTAMP}` in the schema, when the early check would run, then it is not executed for these names.
- **STAG-28** Given a schema without `{TIMESTAMP}` and two sessions with the same planned name, when the run starts, then abort before the chats, no workspace.
- **STAG-29** Given a sink's success and a foreign-PID workspace next to it, when cleanup runs, then the foreign workspace remains.

### stdout-only

- **STAG-30** Given neither `-o` nor `-O` and a usable user temp, when the first non-empty completion is persisted, then a shard is created under `{user temp}/.tmp_staging_stdout_<PID>/`, not immediately `stdout.txt`.
- **STAG-31** Given the same run, when persisting, then no workspace is created in CWD and none under an `-o`/`-O` prefix.
- **STAG-32** Given `$TMPDIR` set to an existing, writable directory, when stdout-only persists, then the shards live under exactly that directory, not under `/tmp`, unless `$TMPDIR` coincides with it.
- **STAG-33** Given user temp is missing or not writable, when stdout-only starts, then abort before the first completion, no workspace.
- **STAG-34** Given finished shards and a successful commit, when output happens, then after Assembly exactly the merged content appears on stdout and the stdout workspace (including shards) is gone.
- **STAG-35** Given only empty shards under stdout-only, when the commit runs, then no reply text appears on stdout and the workspace is gone.
- **STAG-36** Given an error during the stdout commit, when it occurs, then stop immediately, workspace remains under user temp, message names this workspace.

---

## 11. Non-goals (explicitly rejected)

- User temp as the parent of `-o` or `-O`.
- CWD as the parent of stdout-only.
- `-m w` implemented as a copy (target for file sinks is rename, like `-m x`).
- One workspace for two sinks.
- Combined `-o` + `-O` operation in a single run.
- Pre-freezing `{TIMESTAMP}` at process start.
- Mandatory list of already-moved files in the error message.
- Suppressing empty `-O` slots.
- Implicitly creating `DIR` or `FILE.parent`.
- Shell redirection of stdout as a substitute for `-o`.
- A metadata sidecar for shard timestamps (mtime is used instead, Section 6.3).
- A backup copy (`~` suffix) of an existing target file before commit — evaluated and rejected (redundant given the already-atomic rename operation; a standalone versioning feature outside this contract).

---

## 12. Open items outside the core

- Visibility of the workspace path on the `-v` board (especially relevant for stdout-only, since user temp does not sit next to the invocation location).
- A public session placeholder alongside `CHUNK_*`, `LOOP_*`, `TIMESTAMP`.
- The reserved content name `stdout.txt`/`FILE.name` as the Assembly result in the workspace: fixed or arbitrary, as long as it is clearly distinguishable from shards.
- Exact width of the shard sequence number (proposed here: 6 digits) — to be finally confirmed.
- Deletion timing of individual shards after successful Assembly: immediately, or only with the whole workspace on commit success (currently: the latter, see 7.0 point 5).

---

## Appendix A. What "elaborate acceptance criteria in detail" means

Not: implementing tests.

Rather: sharpening each criterion in Section 10 far enough that a later test or review needs no interpretation. Typically per criterion:

- Preconditions (directories, existing files, `$TMPDIR`, `-m`, schema).
- Trigger (first completion, last commit, failure at the n-th rename).
- Observable artefacts (exact workspace paths, shard content, Assembly result, whether CWD stays untouched).
- Postconditions (workspace gone or left in place, target touched or not).

Example, not yet fully worked out: STAG-32 needs `$TMPDIR` set to something other than `/tmp`, and proof that no `res<N>` shards sit under `/tmp` and none in CWD.

---

## Appendix B. Validation workflow

Not: a CI job, a test file, a patch.

Rather: a binding **check order**. A later phase assumes the previous one already meets the target. If a phase fails, later phases are not counted as compensating for it.

Observing the workspace *before* the success cleanup: pause the run after the last persist and before commit, or deliberately make the commit fail. Without this cut, only the post-state is visible. For `-o`/stdout, additionally: pause the run between the end of persist and the start of Assembly, to see the shards before they are merged — this was not possible under v1.0 and is a new observation point.

Shared fixtures, unless contradicted:

- `CWD` = empty working directory, not identical to user temp.
- `DIR` = empty, writable directory.
- `FILE` = `DIR/report.md` or `CWD/report.md`, depending on phase.
- User temp = its own writable directory, set via `$TMPDIR`, **different** from `CWD`, **different** from `/tmp` where the platform allows it.
- Two completions `A` (non-empty), `B` (non-empty), optionally `∅` (empty).
- Schema without `{TIMESTAMP}`: `{CHUNK_FILE_NAME}.txt`, two sessions with different names, except phase B4.
- The run's PID is known, or read from the resulting directory name.

### Phase P — Parents, before anything is persisted

Goal: no workspace, no completion, a clear abort message.

| Step | Given | When | Then | Criteria |
|---|---|---|---|---|
| P1 | `DIR` missing | `-O DIR` starts | Abort before chat; neither `.tmp_staging_dir_*` nor any other prefix | STAG-01 |
| P2 | `DIR` is a file | `-O DIR` starts | As P1 | STAG-01 |
| P3 | `FILE.parent` missing | `-o FILE` starts | Abort; no `.tmp_staging_file_*` | STAG-03 |
| P4 | `$TMPDIR` points to a missing or unwritable directory | stdout-only starts | Abort; no workspace under CWD, `/tmp`, or the unusable path | STAG-33 |
| P5 | valid `DIR` | validation only, no chat yet | no workspace yet (created only before the first persist) | STAG-02 (precondition) |

Stop if any of these aborts leaves a workspace behind.

### Phase G — Happy path per sink alone

Each sink separately. After success: the sink's own workspace is gone, other prefixes never existed.

**G1 `-O DIR -m w`, completions A then B**

- After both persists (cut): `DIR/.tmp_staging_dir_<PID>/` contains two shards, `res000001` (A), `res000002` (B); CWD and user temp have no dragiter workspace.
- After commit: two schema files in `DIR` with content A and B respectively; workspace gone.
- Criteria: STAG-02, STAG-07, STAG-09, STAG-20/STAG-21 analogous for `w`.

**G2 `-o FILE -m w`, FILE not inside an `-O` DIR, completions A then B**

- After both persists: `FILE.parent/.tmp_staging_file_<PID>/` contains shards `res000001` (A), `res000002` (B) — **no** `FILE.name` yet.
- After Assembly (before commit): additionally `FILE.name` with content `A + delimiter + B`, no leading delimiter; shards remain.
- After commit: `FILE` has the same content; `-o` workspace (incl. shards) gone; no `.tmp_staging_dir_*`, no user-temp workspace.
- Criteria: STAG-04, STAG-11, STAG-12, STAG-15, STAG-24.

**G3 stdout-only, `$TMPDIR` = user temp ≠ CWD, completions A then B**

- After both persists: `{user temp}/.tmp_staging_stdout_<PID>/` contains shards `res000001` (A), `res000002` (B); CWD has no `.tmp_staging_*`; `/tmp` has no such workspace if user temp ≠ `/tmp`.
- After Assembly: additionally `stdout.txt` = `A + delimiter + B`.
- After commit: exactly this text on stdout; stdout workspace (incl. shards) gone.
- Criteria: STAG-14, STAG-30, STAG-32, STAG-34.

Stop if a happy path creates the workspace under the wrong parent, or if Assembly starts before persist has finished.

### Phase X — Exclusive and move failures

File sinks only. stdout-only has no `-m x`.

| Step | Given | When | Then | Criteria |
|---|---|---|---|---|
| X1 | `FILE` exists, `-o -m x` | Run starts | Abort before chat, no workspace | STAG-22 / early check |
| X2 | Planned `-O` file exists, schema without timestamp, `-m x` | Run starts | Abort before chat, no workspace | STAG-19, analogous to early check |
| X3 | Two sessions, same planned `-O` name, no timestamp | Run starts | Abort before chats, no workspace | STAG-28 |
| X4 | Workspace full, `-O -m x`, one target only appears by commit time | Commit | No rename, `DIR` unchanged, workspace remains, message with target and workspace | STAG-19, STAG-21 |
| X5 | Two `-O` shards, `-m w`, second rename fails | Commit | First target in `DIR`, second shard plus the rest stay in the workspace, run stops, no third rename | STAG-21 |
| X6 | `-o -m x`, `FILE` missing, Assembly result finished | Commit | Rename, workspace gone | STAG-22 |
| X7 | `-o -m x`, `FILE` exists, Assembly result finished | Commit | No rename, `FILE` old, workspace remains, message | STAG-23 |

Stop if an x-conflict deletes the workspace, or a move failure touches further files.

### Phase D — Reserved, removed in v2.0

Previously covered both file sinks active at once (`-O` and `-o` combined). No longer applicable: `-o` and `-O` are mutually exclusive (Section 1). The letter is kept reserved rather than reused.

### Phase L — Empty semantics

| Step | Sink | Completions | Then | Criteria |
|---|---|---|---|---|
| L1 | `-o` | `∅`, then A | A shard for `∅` (0 bytes) is created; Assembly skips it; `FILE.name` starts with A, no delimiter before it | STAG-08, STAG-11, STAG-13 |
| L2 | `-o` | only `∅` | A shard for `∅` is created; Assembly does not create `FILE.name`; `FILE` not created | STAG-13 |
| L3 | stdout-only | only `∅` | A shard is created; Assembly does not create `stdout.txt`; nothing on stdout; workspace gone after commit | STAG-35 |
| L4 | `-O` | one `∅` among two slots | The empty shard becomes the empty schema file 1:1; exists after success | STAG-16 |
| L5 | `-O -m a`, target has content, new content `∅` | Commit | Existing content unchanged, no dangling delimiter | STAG-17 |

Stop if `-O` swallows empty slots, or Assembly materialises empty blocks for `-o`/stdout.

### Phase I — Isolation

| Step | Given | Then | Criteria |
|---|---|---|---|
| I1 | stdout-only happy path | CWD has no `.tmp_staging_*` | STAG-31 |
| I2 | `-O`-only happy path | User temp has no `.tmp_staging_stdout_*` and no `.tmp_staging_file_*` | STAG-05 |
| I3 | `-o`-only happy path | No `.tmp_staging_dir_*`, no stdout prefix | STAG-04 |
| I4 | Foreign folder `.tmp_staging_dir_1` next to one's own | After one's own success, `_1` remains | STAG-29 |
| I5 | `{TIMESTAMP}` in the `-O` schema | Early check does not run; final name carries the shard mtime | STAG-26, STAG-27 |

### Phase order (binding)

```
P  Parents without persist
G  Happy path per sink (G1 → G2 → G3)
X  Exclusive and move failures
L  Empty
I  Isolation and TIMESTAMP
```

(Phase D is removed; see above.)

P before G, because otherwise happy paths would mask missing parents.
G before X, because move failures are only meaningful against a known, full workspace.
L after X, because empty-value rules would otherwise interact with exclusivity edge cases.
I last: isolation is only credible once all parents and prefixes are individually correct.

### Assessment

- Phase passed: all its steps meet the target, including "no artefact under the wrong parent".
- Profile passed: P–I passed.
- Profile failed: name the first failing phase; later phases do not count as compensation.
