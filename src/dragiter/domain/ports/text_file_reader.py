# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol

from dragiter.domain.models.text_file import TextFile

# --- Protocol (Structural Interface) ---

class TextFileReader(Protocol):
    """
    A structural type (Protocol) for file checking operations.
    Any class that implements a matching 'detect_encoding' method
    implicitly fulfills this protocol. No inheritance required!
    """

    def read(self, tf: TextFile) -> str:
        """
        Read file with given encoding.
        """
        ...  # Using an ellipsis (...) is the pythonic standard for Protocol bodies


class TextFileReaderError(Exception):
    """Raised when a text file cannot be read (missing, oversized, encoding, …)."""
