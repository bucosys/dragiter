# Configuration — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-conf-configuration.md` |
| Code | `CONF` |
| Type | functional |
| Version | 0.5 |
| Status | draft — initial version, describes current code; the `--resume`/`-O` cross-field rule and CONF-34 are *proposed*, not yet implemented |
| Created | 2026-09-24 |
| Related | `ADR-0001`, `AUDT` |

## 1. Purpose

Settings from command line, configuration file, environment and defaults with a defined
precedence; secure handling of API keys; switching providers via `base_url`/`model_name`.

## 2. Scope

In scope:

- Precedence between the four origins for one property: CLI argument > TOML config file
  > environment variable > built-in default.
- Locating the config file itself (`-c` / `$DRAGITER_CONFIG_FILE` /
  `~/.config/dragiter/config.toml`).
- `$VAR` expansion inside config-file and environment values.
- Rebasing relative paths against `-b`/`--base-directory`.
- Type conversion and rejection rules per setting type (bool/int/float/string/path) for
  each origin.
- `ConfigurationValidator`'s mandatory-field, range and cross-field rules that decide
  whether a run may start.
- Masking `api_key` in help text is out of scope here; masking in the activity log is
  `AUDT`'s (`AUDT-11`).

Out of scope: The settings mechanism itself (one `ValueSetting` subclass per property,
write-once, origin field) — settled by `ADR-0001`. Origin values leaking into the
activity log — `AUDT`.

## 3. Terms

| Term | Meaning |
|---|---|
| Origin | Where a value came from: `ValueOrigin.CLI`, `CONFIG`, `CONFIG_RESOLVED`, `ENV`, `ENV_RESOLVED`, `DEFAULT` (`ADR-0001`) |
| Setting | One `ValueSetting` instance identified by its class and `key` string, write-once per run |
| Parameter group | A frozen dataclass grouping related settings (`AIServiceParameters`, `LoggingParameters`, `ExecutionParameters`, `InputParameters`, `OutputParameters`, `WorkspaceParameters`) |
| Rebasing | Recomputing a `PathSetting`'s absolute value against a new base directory after it was first set as a relative path |
| `$VAR` expansion | Replacing a leading `$NAME` in a config-file or environment value with `os.environ["NAME"]` via `os.path.expandvars`, before type conversion |

## 4. Behaviour

### 4.1 Precedence

`ConfigurationLoader.run()` applies origins in this fixed order, each step skipping any
setting that `is_set` already:

1. `_get_args()` — CLI flags via `argparse`, always attempted first, origin `CLI`.
2. `_set_settings_from_config()` — values from the resolved TOML file, origin `CONFIG`
   (or `CONFIG_RESOLVED` after `$VAR` expansion).
3. `_set_settings_from_environment()` — `DRAGITER_<KEY>` variables, origin `ENV` (or
   `ENV_RESOLVED` after expansion).
4. `_rebase_filepath()` — if `-b`/`--base-directory` is set, every relative path setting
   already set (activity file, CA bundle, client cert/key, prompt/loop/resource files,
   `-o`/`-O`) is rebased against it.
5. `_set_factory_defaults()` — currently only `output_mode`, defaulted to `"x"`, origin
   `DEFAULT`, if still unset.

Because every step skips already-set settings, whichever origin sets a value first in
this order wins; a later step never overwrites it.

### 4.2 Locating the config file

`_calculate_config_path`, in order: the `-c`/`--config-file` CLI value (rebased against
`-b` first, if both are given) → `$DRAGITER_CONFIG_FILE` → `~/.config/dragiter/config.toml`
if it exists → `None` (no config file; CLI/env/defaults only, with a warning logged).

### 4.3 `$VAR` expansion

Applied identically for config-file values (`_set_settings_from_config`) and environment
values (`_set_settings_from_environment`): a value starting with `$` is passed through
`os.path.expandvars`. If expansion changes the string, the origin becomes `*_RESOLVED`
and the expanded string is parsed normally; if `expandvars` leaves it unchanged (the
referenced variable does not exist), a warning is logged and the raw string is used as-is
(still parsed by the setting's own type, so a `$MISSING/v1` string setting simply keeps
that literal text, while a numeric setting would fail type conversion on it — see 4.4).
CLI arguments (`argparse`) are never expanded this way.

### 4.4 Type conversion per origin

- CLI: `argparse` produces the target Python type directly (`type=int`/`float`/`Path`, or
  `store_true` for bool) — no separate string-parsing step.
- Config file (TOML): a value that is not already the correct Python type is rejected —
  a `StringSetting` refuses a native TOML integer or boolean, an `IntegerSetting`/
  `FloatSetting` refuses a quoted numeric string, a `BoolSetting` refuses a quoted TOML
  boolean (`"true"`/`"false"`) — TOML's own type must already match. A native
  `bool = false` **does** set the setting to `False` (`is_set=True`), not "unset".
- Environment: everything arrives as a string and goes through `from_string`, which for
  `BoolSetting` accepts (case-insensitively, after `strip()`) `true`/`1`/`yes` as `True`
  and `false`/`0`/`no`/`off`/`n` as `False`, raising `ValueError` on anything else; for
  `IntegerSetting`/`FloatSetting` it strips whitespace then converts, raising on
  non-numeric text; for path/string settings it is a stripped/pass-through assignment.
  This boolean truthy set is the same one `LoggingConfigurator` uses independently for
  `-d`/`-v`/`DRAGITER_DEBUG`/`DRAGITER_VERBOSE` (kept in sync by convention, not by a
  shared implementation).

### 4.5 Validation (`ConfigurationValidator.run`)

Runs once all origins have been applied, before any pipeline worker that touches the
filesystem or network. Raises `ConfigurationValidatorError` carrying every finding at
once (not just the first), except the `-o`/`-O` exclusivity check, which raises alone and
immediately (`STAG-06`) before any other rule is evaluated:

- `-o` and `-O` both set → immediate, sole error.
- Neither a non-blank `task` nor a readable `prompt_file` → error (one or the other is
  mandatory; an unreadable `prompt_file` is its own, separate finding).
- `output_mode` (once defaulted) must be one of `a`/`x`/`w`.
- Not simulating and `base_url` unset → error; simulate mode makes `base_url` optional.
- Every input path setting that is set (`base_directory`, CA bundle, client cert/key,
  loop file, resource file) must be readable.
- Every output path setting that is set (`activity_file`, `log_file`) must have a
  readable parent directory.
- A sink parent (`-O`'s `DIR`, `-o`'s `FILE.parent`) must exist, be a directory and be
  writable — dragiter never creates it (`STAG Section 5.1`).
- Against the effective `output_mode` for `-o`'s target: `x` rejects an existing file,
  `a`/`w` require write access to an existing one.
- `retry_delay` must be `0`–`20` inclusive; `max_retry` is not range-checked here.
- `chars_per_token` must be `> 0.0`.
- `pack_limit_chars` must be `>= 0` (`0` means packing is off, and is accepted).
- `max_chunks` must be `>= 1`.
- `client_key_file` set without `client_cert_file` → error (a private key needs its
  certificate).
- *Proposed:* `--resume` set without `-O` → error. Resume (`STAG` Section 5.4) adopts
  a sibling workspace's shards by directory listing, which only exists for the `-O
  DIR` sink; `-o` and stdout-only are excluded by design, not merely unimplemented.

## 5. Error cases

- Any TOML/env conversion failure raises before the pipeline starts running — never a
  silently-ignored or partially-applied setting.
- `ConfigurationLoader.run()` wraps every exception, including validator-unrelated ones
  from `_get_args`/`read_from_toml`, in `ConfigurationLoaderError`, preserving the cause
  (`ADR-0000, rule 12`).
- `ConfigurationValidatorError` carries the full list of findings (rule, description) so
  a user sees every problem in one run, not one abort per rerun — except the `-o`/`-O`
  exclusivity check, which is reported alone.

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`CONF-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

### Precedence

- **CONF-01** Given a setting supplied both on the CLI and via `DRAGITER_<KEY>`, when
  the loader runs, then the CLI value wins.
- **CONF-02** Given a setting supplied both in the TOML config file and via
  `DRAGITER_<KEY>`, when the loader runs, then the config-file value wins.
- **CONF-03** Given a setting supplied only via `DRAGITER_<KEY>`, when the loader runs
  with no CLI or config-file value for it, then the environment value is applied.
- **CONF-04** Given an environment variable that does not match any `DRAGITER_<KEY>`
  setting name, when the loader runs, then it has no effect on any setting.

### Environment parsing

- **CONF-05** Given `DRAGITER_MODEL_NAME` set to a value with leading/trailing
  whitespace, when applied, then the whitespace is preserved as-is on a string setting
  (only the raw variable name lookup is exact; the string value itself is not stripped).
- **CONF-06** Given `DRAGITER_DEBUG`/other bool settings set to one of `true`/`TRUE`/
  `1`/`yes`/`YES` (any case), when applied, then the setting becomes `True`; given one of
  `false`/`0`/`no`/`off`/`n`, then it becomes `False`.
- **CONF-07** Given `DRAGITER_MAX_CONTEXT_TOKENS`/`DRAGITER_MAX_RETRY` set to a numeric
  string with surrounding whitespace, when applied, then it is parsed as `int` after
  stripping.
- **CONF-08** Given `DRAGITER_CHARS_PER_TOKEN`/`DRAGITER_TEMPERATURE` set to a numeric
  string with surrounding whitespace, when applied, then it is parsed as `float` after
  stripping.
- **CONF-09** Given `DRAGITER_MAX_CONTEXT_TOKENS=abc` (not numeric), when the loader
  runs, then it raises rather than silently ignoring the variable or crashing later in
  the pipeline.
- **CONF-10** Given an environment value starting with `$` whose reference resolves
  (e.g. `$LLM_HOST/v1`), when applied to a string or path setting, then the expanded
  value is used.
- **CONF-11** Given an environment value starting with `$` whose reference does not
  resolve, when applied, then the literal, unexpanded string is used instead of raising.
- **CONF-12** Given an environment value starting with `$` that resolves to a numeric
  string, when applied to an integer or float setting, then expansion happens before
  type conversion and the numeric value is set correctly.

### TOML config file

- **CONF-13** Given a TOML value of the wrong native type for its setting (a native
  integer/boolean for a `StringSetting`, a quoted numeric string for an `IntegerSetting`/
  `FloatSetting`, a quoted boolean string for a `BoolSetting`), when the loader runs,
  then it raises rather than silently coercing.
- **CONF-14** Given a TOML value of the correct native type (native int, float, or an
  unquoted `true`/`false`), when the loader runs, then it is applied with the right
  Python type.
- **CONF-15** Given `simulate = false` (native TOML boolean) in the config file, when
  applied, then the setting is `is_set=True` and `value=False` — not left unset.
- **CONF-16** Given a config file with several differently-typed keys in one document,
  when the loader runs, then every value is converted to its own setting's type
  correctly in a single pass.
- **CONF-17** Given `-c PATH` on the CLI, when the loader resolves the config
  path, then `PATH` is used regardless of `$DRAGITER_CONFIG_FILE` or the default user
  config location.
- **CONF-18** Given no `-c` and no `$DRAGITER_CONFIG_FILE`, when
  `~/.config/dragiter/config.toml` does not exist, then the loader proceeds without a
  config file (CLI/env/defaults only) instead of raising.

### Logging flags (`LoggingConfigurator`)

- **CONF-19** Given no CLI flags and no relevant environment variables, when
  `LoggingConfigurator.parse_and_configure()` runs, then `debug=False`, `verbose=False`,
  `log_level=WARNING`, `log_file=None`.
- **CONF-20** Given `--debug`/`-d` or `DRAGITER_DEBUG` truthy, when configured, then
  `debug=True` and `log_level=DEBUG`; noisy HTTP loggers (`httpx`, `httpx2`, `httpcore`,
  `openai`) are left at `NOTSET`.
- **CONF-21** Given `--verbose`/`-v` or `DRAGITER_VERBOSE` truthy without `--debug`, when
  configured, then `verbose=True`, `log_level` stays `WARNING`, and the noisy HTTP
  loggers are forced to `WARNING`.
- **CONF-22** Given both `--debug` and `--verbose`, when configured, then `debug` wins
  for `log_level` (`DEBUG`), while `verbose` is still recorded `True`.
- **CONF-23** Given `--log-file PATH` (absolute) or a relative one combined with
  `--base-directory`, when configured, then the file handler target is `PATH` resolved
  against that base directory; a CLI `--log-file` takes precedence over
  `$DRAGITER_LOG_FILE`.

### Validation

- **CONF-24** Given neither a non-blank `task` nor a readable `prompt_file`, when
  `ConfigurationValidator.run()` runs, then it raises with a finding naming the missing
  requirement.
- **CONF-25** Given an `output_mode` outside `{a, x, w}`, when validated, then it raises
  naming `output_mode` and the allowed values.
- **CONF-26** Given `retry_delay` outside `0`–`20`, when validated, then it raises naming
  `retry_delay`.
- **CONF-27** Given `chars_per_token <= 0.0`, when validated, then it raises.
- **CONF-28** Given `simulate=True` and `base_url` unset, when validated, then no error
  is raised for `base_url`.
- **CONF-29** Given `simulate=False` and `base_url` unset, when validated, then it
  raises naming `base_url`.
- **CONF-30** Given `client_key_file` set without `client_cert_file`, when validated,
  then it raises naming the missing certificate.
- **CONF-31** Given `pack_limit_chars` negative, when validated, then it raises; given
  exactly `0`, then validation passes.
- **CONF-32** Given `max_chunks` set to `0`, when validated, then it raises naming
  `max_chunks`; given a positive value, then validation passes.
- **CONF-34** *proposed* Given `--resume` set and neither `-o` nor `-O` set, or
  `--resume` set together with `-o`, when `ConfigurationValidator.run()` runs, then it
  raises naming `--resume` and `-O` as the required combination; given `--resume`
  together with `-O`, then validation passes for this rule.

### Secrets in logs

- **CONF-33** Given a CLI-supplied setting whose key contains `key` (e.g. `--api-key`),
  when `ConfigurationLoader._get_args()` logs it at `DEBUG` level, then the logged value
  is masked (`********`), never the real secret; a non-key setting logged the same way
  still shows its real value.

## 7. Open questions

- `max_retry` has a declared setting and CLI/env wiring but no range check in
  `ConfigurationValidator`, unlike its sibling `retry_delay` — confirm whether this is
  intentional before adding a criterion for it.
- `ConfigurationLoader`'s CLI parsing (`argparse`) has no dedicated unit-level acceptance
  criteria here beyond the precedence/integration tests already covering it indirectly
  (CONF-01); a CLI-only parsing spec would need its own fixtures per setting type.

## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.2 (2026-09-25): initial version — precedence, `$VAR` expansion, TOML/env type
  rules, and `ConfigurationValidator`'s mandatory/range/cross-field checks, derived
  from `configuration_loader.py`, `configuration_validator.py`, `settings.py` and
  `logging_configuration.py`.
- 0.3 (2026-09-25): CONF-17 covered by a new test in
  `tests/test_configuration_loader_env_precedence.py`; *proposed* mark dropped.
- 0.4 (2026-09-25): fixed a real secret-leak found during a test-quality audit —
  `_get_args()` logged a CLI-supplied API key in clear text at `DEBUG` level, bypassing
  `APIStringSetting.__repr__`'s existing masking. New CONF-33, with a regression test.
- 0.5 (2026-09-29): *proposed* cross-field rule for the new `--resume` setting
  (`--resume` requires `-O`, `STAG` Section 5.4) — new CONF-34. No behaviour change
  yet; nothing here is implemented.
