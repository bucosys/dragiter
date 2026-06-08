from typing import Protocol, TypeVar, Generic, Optional
from typing import final, get_origin, get_args


from abc import ABC, abstractmethod

T = TypeVar('T')


# --- Protocol (Structural Interface) ---


class Validator(ABC, Generic[T]):
    """Generische abstrakte Basisklasse."""

    def get_type_name(self) -> str:
        """Gibt den Namen des Typs zurück, mit dem T instanziiert wurde."""
        cls = type(self)

        # Hole die Generic-Argumente
        origin = get_origin(cls)
        if origin is None:
            origin = cls

        args = get_args(cls)
        if args:
            concrete_type = args[0]  # T ist das erste Argument
            return concrete_type.__name__ if hasattr(concrete_type, '__name__') else str(concrete_type)

        return "Unknown"


    @final
    def validate(self, object_to_validate: T) -> str :
        ret_val: str = None
        if object_to_validate is None:
            raise ValidationError(f"{self.get_type_name()}: Object to validate cannot be None.")

        try:
            ret_val = self._validate_object(object_to_validate)

        except Exception as e:
            raise ValidationError(f"Unexpected Error: {e}") from e

        if ret_val:
            raise ValidationError(f"{self.get_type_name()}: {ret_val}")

        return self._checksum(object_to_validate)

    @abstractmethod
    def _validate_object(self, obj: T) -> str or None:
        """Must be implemented in subclass"""
        pass

    @final
    def _checksum(self, object_to_validate: T) -> str :
        return "Moin"



class ValidationError(Exception):
    pass


class ValidationResult:
    def __init__(self, is_valid: bool, error: Optional[str] = None, checksum: Optional[str] = None):
        self.is_valid = is_valid
        self.error = error
        self.checksum = checksum