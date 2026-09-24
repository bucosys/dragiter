# Bundled aids — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-help-bundled-aids.md` |
| Code | `HELP` |
| Type | functional |
| Version | 0.2 |
| Status | draft — initial version, describes current code |
| Created | 2026-09-24 |
| Related | — |

## 1. Purpose

`dragiter-gen-docs`, `dragiter-gen-examples` and the information output (`--info`,
`--help`, usage banner), so a user can find documentation, worked examples and the
command-line reference without leaving the terminal.

## 2. Scope

In scope:

- `dragiter` invoked with no arguments: banner plus short usage.
- `dragiter --info`/`-info`/`/info`: the bundled man-page-style help text.
- `dragiter --help`: `argparse`'s own generated help (all registered flags).
- `dragiter-gen-docs [PATH]` and `dragiter-gen-examples [PATH]`: copying the packaged
  `docs/`/`examples/` folder onto the file system.

Out of scope: The content of `docs/manual.md`/`docs/reference.md`/`info.txt` themselves,
and of the example fixtures — this spec covers the delivery mechanism, not their text.

## 3. Terms

| Term | Meaning |
|---|---|
| Info text | `dragiter/docs/info.txt`, packaged with the wheel, printed verbatim by `--info` |
| Banner | The ASCII-art header printed by `InfoPresenter.print_banner()` when `dragiter` runs with no arguments |
| Exported resource | A copy of the packaged `docs/` or `examples/` directory tree written under the target path |

## 4. Behaviour

### 4.1 Pre-selector in `cli.py`

Before any configuration loading: `len(sys.argv) == 1` prints the banner then the usage
text and returns (exit code from `InfoPresenter.show_usage()`, always `0`). Otherwise, if
any argument case-insensitively equals `--info`, `-info` or `/info`, `InfoPresenter.
show_help()` runs and its return code becomes the process exit code — these two checks
happen before `LoggingConfigurator`/`ConfigurationLoader` run at all, so they work even
with an otherwise-invalid or incomplete configuration.

### 4.2 `InfoPresenter`

- `show_usage()`: prints a fixed four-line synopsis (`dragiter --help`, `--info`,
  `dragiter-gen-docs [PATH]`, `dragiter-gen-examples [PATH]`) and returns `0`.
- `show_help()`: reads `docs/info.txt` from the installed package via
  `importlib.resources.files("dragiter")` and prints it unmodified; returns `1` and
  prints an error line (not a traceback) if the resource cannot be read.
- `print_banner()`: prints a fixed ASCII-art banner followed by
  `[dragiter v<version> - Deterministic Context Iterator.]` and a rule line; no return
  value, never raises on its own.
- `--help` itself (a single dash-dash flag recognised by `argparse`) is not handled by
  `InfoPresenter` — it is `ConfigurationLoader._get_args()`'s `argparse.ArgumentParser`
  producing its own generated help and exiting, which only happens once the loader
  actually runs (i.e. after the `--info`/no-argument pre-selector has already let the
  process continue).

### 4.3 `ResourceExporter`

`ResourceExporter.export(resource_name)` (`resource_name` is `"docs"` or `"examples"`,
one static method backing both console-script entry points):

- Target directory: `Path(sys.argv[1])` if a first CLI argument is given, else the
  current working directory; the resource is copied into `<target>/<resource_name>`.
- Copies via `shutil.copytree(..., dirs_exist_ok=True)` — an existing destination is
  merged into, not replaced; files already present with the same name are overwritten by
  `copytree`'s own semantics.
- Missing packaged resource, or any exception during copy, prints a `❌`-prefixed message
  to stderr and calls `sys.exit(1)`; success prints a `✅`-prefixed message to stdout.

## 5. Error cases

- `--info` with a corrupted or missing packaged `info.txt`: caught, printed as
  `Error loading help: <exception>`, process exit code `1` (not a traceback).
- `dragiter-gen-docs`/`dragiter-gen-examples` against a package build that lacks the
  named resource, or a destination that cannot be written to: printed to stderr with a
  `❌` prefix, process exits `1`.

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`HELP-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

None of the criteria below have a dedicated test today (see Open questions) and are
therefore all marked *proposed*, even though the behaviour they describe is already
implemented.

- **HELP-01** *proposed* Given `dragiter` invoked with no arguments, when it runs, then
  the banner is printed followed by the four-line usage synopsis, and the process exits
  `0` without touching configuration loading.
- **HELP-02** *proposed* Given `dragiter --info` (or `-info`/`/info`, any argument
  position, case-insensitive), when it runs, then the packaged `info.txt` is printed
  verbatim and the process exits with `show_help()`'s return code, before
  `LoggingConfigurator`/`ConfigurationLoader` run.
- **HELP-03** *proposed* Given the packaged `info.txt` resource cannot be read, when
  `--info` runs, then an `Error loading help: ...` line is printed and the process exits
  `1`, not a traceback.
- **HELP-04** *proposed* Given `dragiter --help`, when it runs, then `argparse`'s
  generated help listing every registered flag is printed and the process exits `0`.
- **HELP-05** *proposed* Given `dragiter-gen-docs` with no path argument, when it runs,
  then the packaged `docs/` tree is copied to `./docs` under the current working
  directory.
- **HELP-06** *proposed* Given `dragiter-gen-docs PATH`, when it runs, then the packaged
  `docs/` tree is copied to `PATH/docs`, merging into an existing directory rather than
  failing.
- **HELP-07** *proposed* Given `dragiter-gen-examples [PATH]`, when it runs, then
  HELP-05/HELP-06 apply analogously for the packaged `examples/` tree.
- **HELP-08** *proposed* Given a package build where the named resource
  (`docs`/`examples`) does not exist, when the corresponding export command runs, then a
  `❌`-prefixed message is printed to stderr and the process exits `1`.

## 7. Open questions

- No test in `tests/` exercises `InfoPresenter` or `ResourceExporter` at all (confirmed:
  no reference to either class anywhere under `tests/`). `tests/e2e/test_e2e_infrastructure.py`
  only asserts that `--help` triggers `SystemExit(0)` through argparse; it does not touch
  `--info`, the no-argument banner path, or either console-script entry point. All
  HELP-NN criteria above are marked *proposed* purely for this reason — implementing
  their tests (as `HELP-01`… without the mark) is the natural next step, not a code
  change.
- `dragiter --help` is `argparse`'s own mechanism, not `InfoPresenter`'s; whether HELP-04
  belongs in this spec (a functional guarantee: every flag has help text) or is better
  left entirely to `CONF` (which owns `ConfigurationLoader`/`_get_args`) is worth
  revisiting once a test is written.

## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.2 (2026-09-25): initial version — describes the `--info`/no-argument pre-selector,
  `InfoPresenter` and `ResourceExporter` from current code. All criteria marked
  *proposed*: zero existing test coverage for this module.
