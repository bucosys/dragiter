# design/

Design records for dragiter, versioned together with the source code.
Shipped in the sdist, never in the wheel. User documentation lives in `docs/`.

| Directory | Content | Lifecycle |
|---|---|---|
| `adr/` | Architecture decision records | Frozen once accepted; changed only by a superseding ADR |
| `specs/` | Specifications (target state, acceptance criteria) | Living; always describe the current target state |

## Naming

- File names are lower case and start with their type: `adr-NNNN-<title>.md`, `spec-<code>-<title>.md`.
- Every specification has a code of exactly four upper-case letters (`[A-Z]{4}`), registered below.
  A code is never renamed or reused. The specification's header field `Code` repeats it.
- Version, status and creation date belong in the document header, not in the file name.

## Functional and technical specifications

Every specification states its type in the header field `Type` and in the register.

- **functional** — what a user can achieve and rely on, described from the outside:
  inputs, options, visible results, error cases. One functional specification per core
  function of the product.
- **technical** — how dragiter ensures a behaviour internally: mechanisms, sequences,
  invariants. A technical specification serves one or more functional ones and names
  them in its header field `Serves`.

A criterion stays in the specification where it was first defined, even if it would fit
the other type better; the other specification refers to it by identifier.

## Identifiers and references

| Form | Meaning | Example |
|---|---|---|
| `CODE-NN` | Acceptance criterion | `STAG-13` |
| `CODE Section N` / `CODE Sections N–M` | Section(s) of a specification | `STAG Section 7.8` |
| `ADR-NNNN, rule N` | Rule within an ADR | `ADR-0000, rule 8` |

Identifiers and section numbers are never renumbered or reused. A new criterion takes
the next free number; a withdrawn criterion or section stays in place, marked withdrawn
or reserved. Code and tests refer to these identifiers, never to file versions.

A specification describes current behaviour. A planned criterion that is not implemented
yet is written in place and marked *proposed* directly after its identifier, e.g.
`- **CHNK-12** *proposed* Given …`. When it is implemented and tested, the mark is removed.

## Workflow

1. **Specification first.** A change in behaviour starts in the specification: a new or
   changed criterion, or a new section. Code follows, then the tests. A criterion that is
   written now but implemented later is marked *proposed* until then.
2. **Decisions go into ADRs.** A choice between real alternatives with lasting consequences
   is recorded as an ADR. An accepted ADR is not edited; it is superseded by a new one.
3. **One change, one commit.** Specification, code, tests and the CHANGELOG entry of a
   change go into the same commit or merge request, never into separate ones.
4. **References in code are mandatory.** Where code implements a criterion or a section,
   a comment names it (`STAG-13`, `STAG Section 7.8`). Where code follows or deliberately
   deviates from an ADR rule, a comment names the rule (`ADR-0000, rule 8`). The comment
   sits where the behaviour is decided, not on every line that takes part in it.
5. **References in tests are mandatory.** Every test names the criteria it covers in its
   docstring. Every criterion that is neither *proposed* nor *withdrawn* has at least one test.
6. **Check before committing.** `scripts/check-spec-coverage.sh`, `pytest`, `ruff check`
   and `mypy` pass.

## Register of codes

| Code | Type | Specification |
|---|---|---|
| `MATL` | functional | `specs/spec-matl-material.md` — providing and reading material |
| `CHNK` | functional | `specs/spec-chnk-chunking.md` — splitting material into chunks |
| `PRMT` | functional | `specs/spec-prmt-prompt-template.md` — prompt template and placeholders |
| `LOOP` | functional | `specs/spec-loop-iteration.md` — iteration over loop entries |
| `EXEC` | functional | `specs/spec-exec-execution.md` — execution against an LLM |
| `OUTP` | functional | `specs/spec-outp-output.md` — writing results |
| `LIMT` | functional | `specs/spec-limt-limits.md` — context window and hard limits |
| `SIMU` | functional | `specs/spec-simu-simulation.md` — simulation mode |
| `AUDT` | functional | `specs/spec-audt-audit.md` — traceability |
| `CONF` | functional | `specs/spec-conf-configuration.md` — configuration |
| `HELP` | functional | `specs/spec-help-bundled-aids.md` — bundled aids |
| `STAG` | technical | `specs/spec-stag-staging.md` — staging workspace and commit; serves `OUTP` |

A code is registered when its specification file is created.

## Checking

`scripts/check-spec-coverage.sh` enforces the rules above: registered codes, file names,
header fields `Code` and `Type`, criterion identifiers, and that every criterion is referenced by a test.
It reports all findings and exits with status 1 if there are any. Runs with the Bash 3.2 of macOS as well as with current Bash versions.
