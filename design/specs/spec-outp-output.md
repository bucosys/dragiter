# Output — functional specification

| Field | Value |
|---|---|
| Document | `design/specs/spec-outp-output.md` |
| Code | `OUTP` |
| Type | functional |
| Version | 0.1 |
| Status | draft — skeleton, not yet worked out |
| Created | 2026-09-24 |
| Related | `STAG` (technical; its criteria on output, e.g. STAG-06, stay there and are referred to by identifier) |

## 1. Purpose

Writing results as the user sees it: target, file name scheme, write modes x, w and a, and what the user can rely on.

## 2. Scope

In scope: *to be worked out.*

Out of scope: The internal staging and commit mechanism (see `STAG`, technical).

## 3. Terms

*To be worked out.*

## 4. Behaviour

*To be worked out.*

## 5. Error cases

*To be worked out.*

## 6. Acceptance criteria

Normative, testable. Given / when / then. Each criterion carries a stable identifier
`OUTP-NN`, assigned once in sequence and never renumbered or reused. A criterion that
is not implemented yet is marked *proposed* directly after its identifier.

*None yet.*

## 7. Open questions

*None yet.*

## Change history

- 0.1 (2026-09-24): skeleton created.
- 0.1 (2026-09-25): internal cleanup — OutputWriter/ResultBoardService now require real ContextValidationReport/Resources instances (no behavior change).
