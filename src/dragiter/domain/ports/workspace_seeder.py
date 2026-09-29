# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Adopting a leftover sibling workspace into a freshly created one.

Implements ``design/specs/spec-stag-staging.md`` Section 5.4 (Resume).
"""

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class WorkspaceSeeder(Protocol):
    """
    Adopt shards from a sibling workspace into *workspace*, before its first persist.

    Both variants are always constructed at the composition root; the run
    parameters only pick between them (ADR-0000, rules 5 and 6).
    """

    def seed(self, parent: Path, workspace: Path) -> int:
        """
        Adopt shards for *workspace* (already created, empty) under *parent*.

        Returns the number of shards adopted (``0`` if nothing was adopted).
        Must never raise for the ordinary "nothing to adopt" case.
        """
        ...
