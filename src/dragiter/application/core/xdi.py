import copy
import inspect
import logging
from typing import List, Dict, Type, Any, TypeVar, Protocol

from dragiter.domain.common.base_validator import BaseValidator
from dragiter.domain.ports.checksum_generator import ChecksumGenerator

logger = logging.getLogger(__name__)


T = TypeVar("T")



class Worker(Protocol):
    def run(self, **kwargs: Any) -> Any: ...




class ApplicationManager:
    def __init__(self, checksum_generator: ChecksumGenerator):
        self.workers: List['Worker'] = []
        self.store: Dict[Type[Any], Any] = {}
        self._validators: Dict[Type[Any], BaseValidator] = {}
        self._checksum_generator = checksum_generator

    def register(self, worker: Worker, *validators: 'BaseValidator') -> None:
        self.register_worker(worker)
        self.register_validators(*validators)

    def register_worker(self, worker: 'Worker'):
        self.workers.append(worker)

    def register_validators(self, *validators: 'BaseValidator') -> None:
        """
        Automatically registers one or multiple validators by analyzing
        the signature of their validate_object methods.

        Usage:
        registry.register(ValidatorA())
        registry.register(ValidatorA(), ValidatorB(), ValidatorC())
        """
        for validator in validators:
            # 1. Read the method's signature
            sig = inspect.signature(validator.validate_object)

            parameter_found = False

            # 2. Find the parameter representing the object to be validated
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue

                # 3. Extract the type (e.g., SensorData)
                param_type = param.annotation

                # Security check: Did the developer forget the type hint?
                if param_type is inspect.Parameter.empty or param_type is Any:
                    raise ValueError(
                        f"ValueError: The method 'validate_object' in validator '{validator.__class__.__name__}' "
                        f"must have a clear type hint (e.g., obj: SensorData)."
                    )

                # 4. Add to the dictionary
                self._validators[param_type] = validator
                logger.debug(f"Successfully registered: {validator.__class__.__name__} for type {param_type.__name__}")

                parameter_found = True

                # We found our target parameter for this validator, break the inner loop
                # and move to the next validator
                break

            # Fallback if a validator has no parameters at all (except self)
            if not parameter_found:
                raise ValueError(
                    f"ValueError: The validator '{validator.__class__.__name__}' has no target parameter "
                    f"in its 'validate_object' method."
                )

    def provide(self, data: Any) -> None:
        """
        Stores the provided data in the internal store.
        If a validator is registered for the data's type, it validates the data first.
        """
        if data is None:
            return

        data_type = type(data)

        # 1. Check if a validator is registered for this specific type
        validator = self._validators.get(data_type)

        if validator:
            logger.debug(f"Validating '{data_type.__name__}' using '{validator.__class__.__name__}'...")

            # 2. Execute validation.
            # If the object is invalid, this will raise an exception (e.g., ValueError).
            # The exception will bubble up and stop the execution flow.
            validator.validate_object(data)
        else:
            # Optional: Log that no validation is taking place
            logger.debug(f"Type '{data_type.__name__}' has no registered validator. Storing as unvalidated data.")

        # 3. Store the data securely only AFTER it has passed validation
        self.store[data_type] = data

    def validate_worker_dependencies(self, worker: Worker) -> Dict[str, Any]:
        """
        Inspects the signature of the run method and collects the required dependencies.
        Raises an error if a mandatory dependency is missing.
        """
        sig = inspect.signature(worker.run)
        args = {}

        for name, param in sig.parameters.items():
            # Ignore kwargs (**kwargs)
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue

            param_type = param.annotation

            # If there is no type hint or it is Any, we cannot inject it
            if param_type is inspect.Parameter.empty or param_type is Any:
                continue

            # Load from store
            if param_type in self.store:
                args[name] = copy.deepcopy(self.store[param_type])
            elif param.default is inspect.Parameter.empty:
                # No default value and not in store? Abort!
                raise MissingDependencyError(
                    f"Worker '{worker.__class__.__name__}' requires '{param_type.__name__}' "
                    f"for parameter '{name}', but this type is not present in the store."
                )
        return args

    def run(self) -> None:
        try:
            for worker in self.workers:
                # 1. Resolve & validate dependencies
                args = self.validate_worker_dependencies(worker)

                # 2. Execute worker
                logger.debug(f"--- START WORKER: {worker.__class__.__name__} ---")
                result = worker.run(**args)
                logger.debug(f"--- FINISH WORKER: {worker.__class__.__name__} Returning: {result} --- ")


                if isinstance(result, (list, set, tuple)):
                    for item in result:
                        self.provide(item)
                else:
                    self.provide(result)

        except Exception as e:
            raise ApplicationManagerError(f"Failed to execute application manager run cycle: {e}") from e


class MissingDependencyError(Exception):
    """Raised when a worker requires a dependency that is missing from the store."""
    pass

class ApplicationManagerError(Exception):
    """Raised when the application manager encounters an unhandled runtime exception."""
    pass