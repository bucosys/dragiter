import copy
import inspect
import logging
from typing import List, Dict, Type, Any, TypeVar, Protocol

logger = logging.getLogger(__name__)


T = TypeVar("T")



class Worker(Protocol):
    def run(self, **kwargs: Any) -> Any: ...




class ApplicationManager:
    def __init__(self):
        self.workers: List['Worker'] = []
        self.store: Dict[Type[Any], Any] = {}

    def register(self, worker: 'Worker'):
        self.workers.append(worker)

    def provide(self, data: Any):
        if data is not None:
            self.store[type(data)] = data

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
            raise ApplicationManagerError(f"ApplicationManager::run: {e}") from e
            #logger.error(f"Pipeline execution failed: {e}")
            #raise



class MissingDependencyError(Exception):
    """Raised when a worker requires a dependency that is not present in the store."""
    pass

class ApplicationManagerError(Exception):
    """Raised when a worker throws an error."""
    pass