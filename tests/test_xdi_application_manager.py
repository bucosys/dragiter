# =============================================================================
# dragiter - Deterministic Context Iterator
# Copyright (c) 2026 Michael Buchold <michael.buchold@dragiter.app>
#
# This file is part of dragiter.
#
# dragiter is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dragiter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with dragiter. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing (closed-source use, SaaS, etc.), please contact:
# Michael Buchold <michael.buchold@dragiter.app>
# =============================================================================

"""
Unit tests for `ApplicationManager` (dragiter.application.core.xdi).

This is dragiter's reflection-based dependency-injection / pipeline engine:
every registered Worker declares what it needs purely through the type hints
of its `run()` method, ApplicationManager resolves those from an internal
type-keyed store, executes the worker, and files the return value back into
the store by its own type. Every single pipeline step in cli.py
(ConfigurationLoader, ResourceCollector, ChatManager, OutputWriter, ...)
depends on this mechanism working correctly - it had zero dedicated test
coverage before this file.

These tests use small, self-contained dummy Workers/Validators defined
in-module rather than dragiter's real domain classes, so the DI mechanism
itself is verified in isolation, independent of any change to the actual
pipeline steps.

Two tests (`test_untyped_required_parameter_without_default_raises_type_error`,
`test_missing_dependency_with_default_value_uses_workers_own_default`)
specifically document two easy-to-miss, asymmetric edge cases in
`_validate_worker_dependencies()`:
  - a required parameter *with* a type hint that isn't in the store raises a
    clear `MissingDependencyError`;
  - a required parameter *without* a type hint (and without a default) is
    silently skipped by the resolver and only fails later, as a much less
    descriptive `TypeError`, when the worker is actually called.
Both end up wrapped in `ApplicationManagerError` by `run()`, but with very
different underlying causes - worth knowing before debugging a worker that
"mysteriously" fails to run.
"""

from dataclasses import dataclass, field

import pytest

from dragiter.application.core.xdi import (
    ApplicationManager,
    ApplicationManagerError,
    MissingDependencyError,
)
from dragiter.domain.common.base_validator import BaseValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_manager() -> ApplicationManager:
    """
    A fresh ApplicationManager for each test.

    `checksum_generator` is a structural Protocol that ApplicationManager
    currently only stores (it is not exercised by any of the mechanics under
    test here), so a plain `object()` stand-in is enough.
    """
    return ApplicationManager(checksum_generator=object())


# ---------------------------------------------------------------------------
# Dummy domain types used across several tests
# ---------------------------------------------------------------------------


@dataclass
class Number:
    value: int


@dataclass
class DoubledNumber:
    value: int


@dataclass
class Summary:
    text: str


# ---------------------------------------------------------------------------
# Tests: type-based resolution across a chained pipeline
# ---------------------------------------------------------------------------


def test_run_resolves_dependencies_by_type_across_chained_workers():
    """
    The core "magic": three workers chained purely by type hints, with no
    explicit wiring. Worker 2 consumes what Worker 1 produced, Worker 3
    consumes what Worker 2 produced, and every intermediate result also
    stays available in the store under its own type.
    """

    class ProvideNumberWorker:
        def run(self) -> Number:
            return Number(5)

    class DoubleNumberWorker:
        def run(self, n: Number) -> DoubledNumber:
            return DoubledNumber(n.value * 2)

    class SummarizeWorker:
        def run(self, d: DoubledNumber) -> Summary:
            return Summary(f"Doubled value is {d.value}")

    manager = make_manager()
    manager.register_worker(ProvideNumberWorker())
    manager.register_worker(DoubleNumberWorker())
    manager.register_worker(SummarizeWorker())

    manager.run()

    assert manager.store[Number].value == 5
    assert manager.store[DoubledNumber].value == 10
    assert manager.store[Summary].text == "Doubled value is 10"


def test_run_unpacks_list_result_and_stores_each_item_by_its_own_type():
    """
    A worker may return a list/tuple/set of differently-typed objects
    (dragiter's own ConfigurationLoader does exactly this, returning a list
    of many different ValueSetting subtypes). Each item must be filed into
    the store individually, under its own concrete type.
    """

    @dataclass
    class Foo:
        val: str

    @dataclass
    class Bar:
        val: str

    class ListReturningWorker:
        def run(self) -> list:
            return [Foo("foo-val"), Bar("bar-val")]

    manager = make_manager()
    manager.register_worker(ListReturningWorker())

    manager.run()

    assert manager.store[Foo].val == "foo-val"
    assert manager.store[Bar].val == "bar-val"


# ---------------------------------------------------------------------------
# Tests: error paths
# ---------------------------------------------------------------------------


def test_run_raises_missing_dependency_error_wrapped_in_application_manager_error():
    """
    A worker requiring a typed dependency that was never provided must abort
    the whole run with a clear, worker- and parameter-specific error.
    """

    class NeedsUnprovidedType:
        def run(self, x: Summary) -> None:
            return None

    manager = make_manager()
    manager.register_worker(NeedsUnprovidedType())

    with pytest.raises(ApplicationManagerError) as exc_info:
        manager.run()

    assert isinstance(exc_info.value.__cause__, MissingDependencyError)
    assert "NeedsUnprovidedType" in str(exc_info.value.__cause__)
    assert "Summary" in str(exc_info.value.__cause__)


def test_missing_dependency_with_default_value_uses_workers_own_default():
    """
    If a typed parameter isn't in the store but the worker declared a
    default for it, no error is raised - the resolver simply omits that
    argument and the worker's own default kicks in.
    """

    class NeverProvided:
        pass

    received = {}

    class DefaultFallbackWorker:
        def run(self, missing: NeverProvided = "fallback-value") -> None:
            received["value"] = missing
            return None

    manager = make_manager()
    manager.register_worker(DefaultFallbackWorker())

    manager.run()

    assert received["value"] == "fallback-value"


def test_untyped_required_parameter_without_default_raises_type_error():
    """
    See module docstring: an untyped, default-less parameter is invisible to
    the resolver (it can't know what to inject), so no MissingDependencyError
    is raised at the resolution stage. The failure only surfaces once Python
    itself calls the worker and finds the required argument missing.
    """

    class UntypedRequiredParamWorker:
        def run(self, mystery) -> None:
            return None

    manager = make_manager()
    manager.register_worker(UntypedRequiredParamWorker())

    with pytest.raises(ApplicationManagerError) as exc_info:
        manager.run()

    assert isinstance(exc_info.value.__cause__, TypeError)


# ---------------------------------------------------------------------------
# Tests: store semantics
# ---------------------------------------------------------------------------


def test_worker_receives_deep_copy_not_the_stored_instance():
    """
    Workers must not be able to corrupt shared state: mutating the object a
    worker receives must never affect the instance still held in the store.
    """

    @dataclass
    class Basket:
        items: list = field(default_factory=list)

    class MutatingWorker:
        def run(self, basket: Basket) -> None:
            basket.items.append("mutated-by-worker")
            return None

    manager = make_manager()
    original = Basket(items=["original"])
    manager.provide(original)
    manager.register_worker(MutatingWorker())

    manager.run()

    assert original.items == ["original"]
    assert manager.store[Basket].items == ["original"]


def test_provide_with_none_is_a_no_op():
    """Workers commonly return None (e.g. a validation-only step); provide()
    must silently ignore that instead of storing a NoneType entry."""
    manager = make_manager()

    manager.provide(None)

    assert manager.store == {}


# ---------------------------------------------------------------------------
# Tests: validator integration
# ---------------------------------------------------------------------------


@dataclass
class Payload:
    amount: int


class PayloadValidator(BaseValidator[Payload]):
    def validate_object(self, obj: Payload) -> None:
        if obj.amount < 0:
            raise ValueError("amount must not be negative")


def test_provide_runs_registered_validator_and_stores_on_success():
    manager = make_manager()
    manager.register_validators(PayloadValidator())

    manager.provide(Payload(amount=5))

    assert manager.store[Payload].amount == 5


def test_provide_raises_when_registered_validator_rejects_object():
    manager = make_manager()
    manager.register_validators(PayloadValidator())

    with pytest.raises(ValueError, match="amount must not be negative"):
        manager.provide(Payload(amount=-1))

    assert Payload not in manager.store


def test_register_validators_requires_type_hint_on_target_parameter():
    """A validator whose validate_object() parameter has no type hint can't
    be matched to a store type, so registration must fail loudly."""

    class UntypedValidator(BaseValidator):
        def validate_object(self, obj) -> None:
            pass

    manager = make_manager()

    with pytest.raises(ValueError, match="clear type hint"):
        manager.register_validators(UntypedValidator())


def test_register_validators_requires_at_least_one_parameter():
    """A validator without any target parameter (besides self) has nothing
    to bind to and must be rejected at registration time."""

    class NoParamValidator(BaseValidator):
        def validate_object(self) -> None:
            pass

    manager = make_manager()

    with pytest.raises(ValueError, match="no target parameter"):
        manager.register_validators(NoParamValidator())
