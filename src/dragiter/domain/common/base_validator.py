from abc import ABC, abstractmethod
from typing import TypeVar, Generic

# 1. We define a variable for the type of our arbitrary object (K)
T = TypeVar('T')


# ==========================================
# Base class B
# ==========================================
class BaseValidator(ABC, Generic[T]):
    """
    Abstract base class for all validators.
    It is generic and binds to type T.
    """

    @abstractmethod
    def validate_object(self, obj: T) -> None:
        """
        Validates the object.
        If the check is OK, nothing happens (returns None).
        Otherwise, an exception is raised.
        """
        pass


# ==========================================
# Arbitrary class object K
# ==========================================
class SensorData:
    def __init__(self, temperature: float, status: str):
        self.temperature = temperature
        self.status = status


# ==========================================
# Corresponding validator class V
# ==========================================
class SensorDataValidator(BaseValidator[SensorData]):
    """
    This validator is strictly bound to the 'SensorData' class.
    """

    def validate_object(self, obj: SensorData) -> None:
        if obj.temperature > 180.0:
            # Raise an error if something is wrong
            raise ValueError(f"Overheating! Temperature {obj.temperature}°C is too high.")

        if obj.status != "OK":
            raise ValueError(f"Invalid status: {obj.status}")

        # If the logic reaches this point, the object is valid.
        # "Nothing" happens (implicit return None).