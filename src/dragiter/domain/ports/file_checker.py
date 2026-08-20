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

import pathlib
from typing import Protocol

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

    def detect_encoding(self, path: str | pathlib.Path) -> str:
        """
        Analyzes the file and returns the detected text encoding.
        The implementation details are left to the concrete class.
        """
        ...  # Using an ellipsis (...) is the pythonic standard for Protocol bodies
