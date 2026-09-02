# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Any, Protocol


class ChecksumGenerator(Protocol):
    """
    A structural type (Protocol) for file checking operations.
    Any class that implements a matching 'detect_encoding' method
    implicitly fulfills this protocol. No inheritance required!
    """

    def compute_checksum(self, obj: Any) -> str:
        """
        Optimized checksum calculation
        """
        ...  # Using an ellipsis (...) is the pythonic standard for Protocol bodies
