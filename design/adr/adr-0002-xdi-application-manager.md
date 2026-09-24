# ADR-0002: Type-keyed worker broker (xdi `ApplicationManager`)

| Field | Value |
|---|---|
| Status | accepted — settled |
| Decided | initial design, before the ADR process |
| Recorded | 2026-09-24 (retrospectively) |
| Scope | `src/dragiter/application/core/xdi.py`, wiring in `src/dragiter/cli.py` |

## Context and problem

dragiter runs as a pipeline of workers (loader, validator, resource collector, tokenizer,
loop builder, prompt creator, message builder, context window estimator, chat manager,
output writer). Each worker needs the products of earlier workers. Wiring belongs at the
edge (ADR-0000, rule 5); business logic must not locate its own collaborators.

## Decision

A small in-house broker, `ApplicationManager`, connects the workers.

- Workers are registered in `cli.py`, the composition root. Registration order is
  execution order.
- A worker declares what it needs through the type annotations of its `run` method.
  The broker resolves each annotated parameter from a store keyed by type.
- Whatever a worker returns is provided to the store under its type; a list, set or
  tuple is provided item by item.
- A validator can be registered per type; it is found through the annotation of its
  `validate_object` method and runs before the object is stored.
- Results that are `ActivityProvider`s are written to the activity log.
- Every injected object is a deep copy, so no worker can change another worker's input.

## Considered options

- **In-house type-keyed broker (chosen).** Small, no dependency, explicit order.
- **Hand-written calls in `cli.py`.** Rejected: every new worker changes the call chain
  and the passing of intermediate results by hand.
- **A DI container library.** Rejected: additional runtime dependency for a linear pipeline.
- **Event bus.** Rejected: implicit order, harder to follow for a deterministic tool.

## Consequences

The broker is deliberately simple. Current behaviour at the time of recording, an
inventory rather than a commitment (see "Settled"):

- The store holds one object per exact type; a later object of the same type replaces
  the earlier one. Lookup uses the exact annotation, not subclass matching.
- A worker result of `None` is not stored; workers without a product return `None`.
- Types without a registered validator are stored unvalidated.
- Parameters without annotation, or annotated `Any`, are not injected.
- A parameter with a default whose type is not in the store receives its default.
  As of 2026-09-25 no worker relies on this anymore (the `OutputWriter.run`
  defaults for `context_report` and `resources` were removed; ADR-0000, rules 2
  and 4); the broker still supports the mechanism for any future worker that
  needs it.
- There is no dependency graph; a wrong registration order surfaces as
  `MissingDependencyError` at run time.
- Deep copies cost time and memory in exchange for isolation (ADR-0000, rule 6).

## Settled

The concept is not open for change: a type-keyed broker, workers supplied through the
annotations of `run`, wiring in `cli.py`. Replacing it by a DI library, an event bus or
hand-written wiring is out of scope; reviews, human or AI, do not propose it. Changing the
concept requires a new ADR that supersedes this one.

The implementation may be improved without a new ADR as long as the concept is kept,
for example mandatory validators or a warning or error when a type in the store is
replaced. Such improvements update the inventory above.
