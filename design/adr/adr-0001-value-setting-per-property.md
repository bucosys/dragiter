# ADR-0001: One ValueSetting subclass per configuration property

| Field | Value |
|---|---|
| Status | accepted — settled |
| Decided | initial design, before the ADR process |
| Recorded | 2026-09-24 (retrospectively) |
| Scope | `src/dragiter/domain/models/settings.py`, `parameters.py`, `application/config/` |

## Context and problem

dragiter receives its properties from four origins: command line, configuration file,
environment and built-in defaults (`ValueOrigin`). Each property must be typed, must
record where its value came from, must be set exactly once per run, and must be
unmistakable for any other property of the same data type — a model name must never
be passed where a base URL is expected, although both are strings.

## Decision

Every property that can be supplied from outside is its own class, derived from a typed
intermediate class (`StringSetting`, `IntegerSetting`, `FloatSetting`, `BoolSetting`,
`PathSetting`, `APIStringSetting`), which in turn derives from `ValueSetting[T]`.

- The class is the identity of the property. Within a run there is exactly one instance
  per property, so it behaves like a singleton without being one technically.
- A value is written once (`set` raises on a second call) and carries key and origin.
- Parsing from text is the responsibility of each typed intermediate class (`from_string`).
- Properties are grouped into frozen parameter dataclasses (`AIServiceParameters`,
  `ExecutionParameters`, …), which are what workers receive.

## Considered options

- **One class per property (chosen).** Identity at type level, checked by mypy.
- **One generic instance per data type with a key string**, e.g. `StringSetting("model")`.
  Rejected: two string properties are indistinguishable to the type checker.
- **Plain dataclass or dict of primitive values.** Rejected: no origin, no write-once,
  no masking of secrets.
- **A settings library (e.g. pydantic-settings).** Rejected: additional runtime
  dependency; origin tracking and write-once semantics would have to be rebuilt on top.

## Consequences

Good: type identity for every property, write-once values, origin reporting in the
activity log, secrets masked in `repr` (`APIStringSetting`).

Accepted costs: one class per property (currently more than thirty); adding a property
touches `settings.py`, `parameters.py` and the configuration loader; `from_string` is
enforced at runtime (`NotImplementedError`), not statically.

## Settled

The principle is not open for change: one class per property, derived from a typed
intermediate class, written once. Replacing it by a generic, dict-based or library-based
configuration is out of scope; reviews, human or AI, do not report the per-property
classes as duplication or boilerplate. Changing the principle requires a new ADR that
supersedes this one.

The implementation may be improved without a new ADR as long as the principle is kept,
for example stricter typing of `_key`, abstract methods instead of `NotImplementedError`,
or removing duplicated checks in the intermediate classes.
