# Traceability — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-audt-audit.md` |
| Code | `AUDT` |
| Type | functional |
| Version | 0.2 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | `CONF` |

## 1. Purpose

Activity log and checksums, so that a run can be reconstructed afterwards. Every pipeline
result that carries the `ActivityProvider` protocol is written to the activity log
automatically (`ADR-0002`); no worker calls the logger itself.

## 2. Scope

In scope:

- `ActivityProvider` / `ActivityLogger` protocols.
- `BufferedActivityLogger` (in-memory buffering, activity-record shape) and
  `FileActivityLogger` (JSONL sync to the `-a`/`--activity-file` target).
- Masking of setting values whose key looks like a secret.
- The exception record written by `write_exception`.
- The underlying JSONL line-integrity guarantee (`append_jsonl_to_file`).

Out of scope:

- `ChecksumGenerator` / `BasicChecksumGenerator`. Both exist (a port and one
  implementation, `sha256` over a canonicalised object graph) and `ApplicationManager`
  is constructed with one (`cli.py`), but nothing in the current pipeline ever calls
  `compute_checksum`. There is no checksum-based traceability yet — see Open questions.
- The settings mechanism itself and origin tracking on `ValueSetting` (`ADR-0001`).
- Configuration precedence and validation (see `CONF`).

## 3. Terms

| Term | Meaning |
|---|---|
| Activity record | One `dict` appended to the log, always carrying `TS` (UTC timestamp) and `RT` (the record type: the producing class's name, or `"Exception"`) |
| Activity log | The ordered sequence of activity records for one run |
| Buffer | `BufferedActivityLogger.activity_dict_list`: records held in memory until (if ever) synced to a file |
| Sync | `FileActivityLogger` appending the buffer to the activity file and clearing it |
| Masking | Replacing a setting's real value with the literal string `"***MASKED***"` in its activity record |

## 4. Behaviour

### 4.1 Wiring

`ApplicationManager.provide()` calls `activity_logger.write_activity(result)` for every
worker result that is an `ActivityProvider` instance (`ADR-0002`) — this is automatic and
not something a worker or spec author configures per pipeline step. `cli.py` constructs
exactly one `FileActivityLogger()` for the whole run.

### 4.2 Buffering (`BufferedActivityLogger`)

- On construction, the buffer starts with one seed record:
  `{"TS": <now, UTC>, "RT": <first superclass name>, "initial_status_message": "<tool>(<version>) process started"}`.
  For `FileActivityLogger` (which subclasses `BufferedActivityLogger`), `RT` here is
  `"BufferedActivityLogger"` — the seed record's `RT` names the logger's own base class,
  not the run's subject, because it is read from `self.__class__.__bases__[0]` before any
  real activity has occurred.
- `write_activity(provider)`: calls `provider.to_activity_dict_list()`, and appends one
  record per returned `dict`, each stamped with a shared `TS` for this call and
  `RT = type(provider).__name__`.
- `write_exception(e)`: appends exactly one record `{"TS", "RT": "Exception", "type",
  "message", "module", "traceback", "location", "filename", "lineno"}`. `location`,
  `filename` and `lineno` come from the exception's last traceback frame and are `None`
  if `e.__traceback__` is falsy.

### 4.3 File sync (`FileActivityLogger`)

`FileActivityLogger` overrides both write methods to call `_sync_buffer_to_file()` after
delegating to `BufferedActivityLogger`:

1. The first time any buffered record contains the key `"activity_file"`, the logger
   remembers this permanently (`activity_file_found = True`) and reads that record's
   value as `activity_file_path` (a JSON-serialised setting value — `None` unless the run
   passed `-a`/`--activity-file`).
2. Until that key has appeared, nothing is written; the buffer keeps growing.
3. Once `activity_file_found` is `True` and `activity_file_path` is `None` (the setting
   exists on `LoggingParameters` but the user never gave `-a`), every sync from then on
   — including this one — discards the entire buffer without writing anything.
4. Once `activity_file_found` is `True` and `activity_file_path` is a real path, the sync
   appends every currently buffered record (including everything accumulated before
   `-a`'s value became known, e.g. the seed record) as JSONL and clears the buffer. Every
   later `write_activity`/`write_exception` call appends and syncs immediately.

`LoggingParameters` (an `ActivityProvider` via `ValueSettingsActivityProvider`) is what
usually carries the `"activity_file"` key into the log, once `ConfigurationLoader`'s
result is provided to the pipeline store.

### 4.4 Masking

`ValueSettingsActivityProvider.to_activity_dict_list()` iterates the dataclass fields of
a parameter group (`AIServiceParameters`, `LoggingParameters`, …); for each field that is
a `ValueSetting`, it emits `{setting.key: value}`, where `value` is the literal string
`"***MASKED***"` whenever the substring `"key"` occurs anywhere in `setting.key` (e.g.
`api_key`), and the real `.value` otherwise. This is a substring match on the property's
own key name, not a type check — any future setting whose key happens to contain `"key"`
is masked the same way, and one that doesn't (a certificate path, say) is emitted in the
clear. `APIStringSetting.__repr__` masks separately, for log/debug output, independent of
this activity-record masking.

### 4.5 Underlying JSONL writer

`append_jsonl_to_file` (`infrastructure/io/io_services.py`) is what both loggers use to
persist records. It must keep every record on exactly one physical line: `json.dumps(...,
ensure_ascii=False)` does not escape U+0085 (NEL), U+2028 (LINE SEPARATOR) or U+2029
(PARAGRAPH SEPARATOR), which are line breaks to a naive `splitlines()` reader, so the
writer must still emit them only inside an escaped `\uXXXX` sequence.

## 5. Error cases

- `write_exception` never raises for a missing traceback; the three frame-derived fields
  are `None` instead.
- A record whose content contains U+0085/U+2028/U+2029 must not corrupt file structure —
  it must still decode back to the original string after a per-line JSON parse.

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`AUDT-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

- **AUDT-01** Given a record whose string content contains U+0085, U+2028 or U+2029,
  when it is appended via `append_jsonl_to_file`, then the file gains exactly one new
  physical line and the content round-trips losslessly through `json.loads`.
- **AUDT-02** Given several records appended in one call, each containing a different
  line-breaking character, when read back, then each occupies exactly one physical line
  and all round-trip correctly.
- **AUDT-03** Given two separate `append_jsonl_to_file` calls against the same path, when
  the second call runs, then the first call's lines are preserved unchanged and the new
  lines are appended after them.
- **AUDT-04** Given ordinary Unicode content (emoji, CJK, umlauts) with no line-breaking
  characters, when appended, then it appears unescaped and readable in the raw file
  (`ensure_ascii=False`).
- **AUDT-05** Given content with U+0085/U+2028/U+2029 mixed with harmless ASCII records
  in the same call, when appended, then only the dangerous characters are escaped and no
  physical line contains a raw occurrence of any of them.
- **AUDT-06** Given a fresh `BufferedActivityLogger`/`FileActivityLogger`,
  when it is constructed, then its buffer contains exactly one seed record with keys
  `TS`, `RT` and `initial_status_message`.
- **AUDT-07** Given an `ActivityProvider` result produced by a pipeline
  worker, when `ApplicationManager.provide()` stores it, then `write_activity` is called
  with that exact object, without the worker itself referencing the logger.
- **AUDT-08** Given a run without `-a`/`--activity-file`, when the buffer
  first observes a record containing the key `"activity_file"` with value `None`, then
  the entire buffer (including the seed record and everything logged so far) is
  discarded and no activity file is ever created for the rest of the run.
- **AUDT-09** Given a run with `-a PATH`, when the buffer first observes a
  record containing `"activity_file": PATH`, then every record accumulated so far,
  including the seed record, is written to `PATH` as JSONL in one call, and the buffer is
  empty afterwards.
- **AUDT-10** Given an activity file already resolved to a real path, when a
  further `write_activity` or `write_exception` call happens, then its record(s) are
  appended to the same file immediately, without re-checking or re-reading earlier ones.
- **AUDT-11** Given an `AIServiceParameters` instance with `api_key_string_setting`
  set, when its activity record is produced, then the emitted value for that key is the
  literal string `"***MASKED***"`, never the real key.
- **AUDT-12** Given any other, non-key-named setting (e.g. `model_name`),
  when its activity record is produced, then the real value is emitted unmasked.
- **AUDT-13** Given an exception with a live traceback, when
  `write_exception` runs, then the record's `filename`/`lineno`/`location` match the
  traceback's last frame, and `type`/`message`/`module` match the exception.
- **AUDT-14** Given an exception without a traceback (`e.__traceback__` is
  falsy), when `write_exception` runs, then `filename`/`lineno`/`location` are `None`
  instead of raising.

## 7. Open questions

- The Purpose above (inherited from the skeleton) mentions "the origin of every setting
  value", but `ValueSettingsActivityProvider.to_activity_dict_list()` currently emits
  only each setting's (possibly masked) value, never its `ValueOrigin` (CLI/CONFIG/ENV/
  DEFAULT/…), even though that origin is tracked on every `ValueSetting` instance
  (`ADR-0001`). Either the activity record should be extended to include origin, or this
  spec's Purpose should be narrowed to drop that claim — decide before AUDT-11/AUDT-12
  are implemented as tests.
- `ChecksumGenerator`/`BasicChecksumGenerator` are wired into `ApplicationManager` but
  never invoked; there is no criterion for checksum behaviour here because there is no
  integration point yet to observe. Decide whether checksums are still intended
  (`ApplicationManager` per-object checksums on store writes?) or should be removed as
  dead wiring — see `ADR-0002`'s inventory.
- `BufferedActivityLogger`, `FileActivityLogger`, the masking rule and the exception
  record are now covered by `tests/test_activity_logger.py` (AUDT-06–14), alongside the
  lower-level `append_jsonl_to_file` primitive (AUDT-01–05).

## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.2 (2026-09-25): initial version — describes `ActivityProvider`/`ActivityLogger`,
  buffering, file-sync gating, masking and the exception record from current code;
  flags the missing origin field and the unused `ChecksumGenerator` as open questions.
- 0.2 (2026-09-25): added `tests/test_activity_logger.py`; AUDT-06–14 no longer
  *proposed*. Origin field and `ChecksumGenerator` open questions unchanged.
