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
Filename sanitisation and path containment helpers.

These utilities protect against path traversal and the creation of
unsafe file names when user-controlled or material-derived values
are interpolated into output_filename_schema.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath


# Characters that are never allowed in a generated filename component.
_UNSAFE_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Sequences that attempt to leave the intended directory.
_TRAVERSAL_RE = re.compile(r'(^|/|\\)\.\.($|/|\\)')


def sanitize_filename(name: str, *, max_length: int = 200, fallback: str = "output") -> str:
    """
    Return a safe single-component filename derived from *name*.
    """
    if name is None:
        return fallback

    cleaned = str(name).strip()
    if not cleaned:
        return fallback

    # Neutralise path separators and traversal
    cleaned = cleaned.replace("\\", "_").replace("/", "_")
    cleaned = _TRAVERSAL_RE.sub("_", cleaned)
    cleaned = cleaned.replace("..", "_")

    # Remove unsafe characters
    cleaned = _UNSAFE_CHARS_RE.sub("_", cleaned)

    # Collapse runs of underscores / dots
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip(" ._")

    # Truncate while trying to keep extension
    if len(cleaned) > max_length:
        stem, dot, suffix = cleaned.rpartition(".")
        if dot and 1 <= len(suffix) <= 10 and stem:
            keep = max_length - len(suffix) - 1
            cleaned = f"{stem[:keep]}.{suffix}" if keep > 0 else cleaned[:max_length]
        else:
            cleaned = cleaned[:max_length]

    if not cleaned or cleaned in {".", ".."}:
        return fallback

    return cleaned


def ensure_path_within_directory(candidate: Path, base_directory: Path) -> Path:
    """
    Ensure that *candidate* resolves to a location inside *base_directory*.
    """
    resolved_base = base_directory.resolve()
    resolved_candidate = candidate.resolve()

    try:
        if not resolved_candidate.is_relative_to(resolved_base):
            raise ValueError(
                f"Path traversal detected: {candidate} resolves outside "
                f"the allowed directory {base_directory}"
            )
        else:
            # Fallback
            common = Path(resolved_candidate).parts
            base_parts = resolved_base.parts
            if common[:len(base_parts)] != base_parts:
                raise ValueError(
                    f"Path traversal detected: {candidate} resolves outside "
                    f"the allowed directory {base_directory}"
                )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            f"Unable to verify path containment for {candidate}: {exc}"
        ) from exc

    return resolved_candidate