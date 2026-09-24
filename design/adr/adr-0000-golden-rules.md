# ADR-0000: Golden Rules for Parameter & Dependency Design (Short Form)

1. No null-object fallback. Custom-class parameters always get a real instance.
2. No defaults for required dependencies. Missing param = call error, not fallback.
3. Validate, don't decide. Reject invalid input; never substitute a default.
4. Variants via Protocols, not Optional. Always a concrete implementer, never None.
5. Wiring belongs at the edge (DI/composition root), never in business logic.
6. No runtime mutation of injected dependencies after construction.
7. Exceptions must be explicit and documented (code comment + ADR reference).
8. Tests must treat missing required params as failures, not fallback successes.
9. Service dependency ≠ domain data. Rules 1–6 apply to collaborators, not to
   fields where None is a genuine domain value (prefer an is_set + value
   sentinel there instead of overloading None).
10. No boolean flag selecting an implementation. Pass the implementation
    itself, not a flag the method translates into one.
11. No mutable default arguments.
12. Fail-fast preserves the original cause. Always `raise ... from e` when
    wrapping exceptions.
13. Runtime-checkable Protocols only verify method names, not signatures —
    don't rely on isinstance() alone where that matters.
