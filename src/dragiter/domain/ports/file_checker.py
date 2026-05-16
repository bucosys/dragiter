import codecs
import pathlib
from typing import Union, List, Optional, Protocol


# --- Custom Exceptions ---

class EmptyFileError(ValueError):
    """Raised when the provided file is completely empty."""
    pass


class BinaryFileError(ValueError):
    """Raised when the provided file appears to be binary data, not text."""
    pass


# --- Protocol (Structural Interface) ---

class FileChecker(Protocol):
    """
    A structural type (Protocol) for file checking operations.
    Any class that implements a matching 'detect_encoding' method
    implicitly fulfills this protocol. No inheritance required!
    """

    def detect_encoding(self, path: Union[str, pathlib.Path]) -> str:
        """
        Analyzes the file and returns the detected text encoding.
        The implementation details are left to the concrete class.
        """
        ...  # Using an ellipsis (...) is the pythonic standard for Protocol bodies


