# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Filename sanitisation and path containment helpers.

These utilities protect against path traversal and the creation of
unsafe file names when user-controlled or material-derived values
are interpolated into output_filename_schema.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
import time
from typing import Any

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


def sortable_timestamp() -> str:
    """Return a lexicographically sortable UTC timestamp with nanoseconds."""
    return format_timestamp_ns(time.time_ns())


def format_timestamp_ns(ns: int) -> str:
    """Format a nanosecond epoch value (e.g. a file's ``st_mtime_ns``) for ``{TIMESTAMP}``."""
    seconds = ns // 1_000_000_000
    nanoseconds = ns % 1_000_000_000
    dt = datetime.fromtimestamp(seconds, tz=UTC)
    return dt.strftime("%Y%m%d_%H%M%S_") + f"{nanoseconds:09d}"


def schema_has_runtime_tokens(template: str | None) -> bool:
    """True when the filename schema can only be resolved at write time."""
    return "TIMESTAMP" in (template or "")


def format_output_filename(
    chunk: Any | None = None,
    loop_dict_item: dict[str, Any] | None = None,
    session_index: int | None = None,
    template: str = "",
    *,
    timestamp: str | None,
) -> str:
    """
    Format a single-component output filename from a schema template.

    *timestamp* is the value for ``{TIMESTAMP}``. The caller decides where it
    comes from (shard mtime at commit, clock for simulate boards). ``None`` is
    only allowed when the template does not use ``{TIMESTAMP}``.
    """
    result = template or ""
    if timestamp is None and schema_has_runtime_tokens(result):
        raise ValueError(
            "output_filename_schema uses {TIMESTAMP}, but no timestamp was supplied."
        )
    d: dict[str, Any] = {}

    if chunk:
        d["CHUNK_NUM_ID"] = chunk.num_id if chunk.num_id is not None else 0
        d["CHUNK_FILE_NAME"] = sanitize_filename(chunk.filename or "file")
        d["CHUNK_SECTION_NAME"] = sanitize_filename(chunk.section_name or "section")
        d["CHUNK_SECTION_NUM_ID"] = (
            chunk.section_num_id if chunk.section_num_id is not None else 0
        )

    if loop_dict_item:
        for key, value in loop_dict_item.items():
            if key.endswith("_NUM_ID") or key == "LOOP_NUM_ID":
                try:
                    d[key] = int(value)
                except (ValueError, TypeError):
                    d[key] = session_index or 0
            elif isinstance(value, (int, float)):
                d[key] = value
            else:
                d[key] = sanitize_filename(str(value))

        if "LOOP_NUM_ID" not in d:
            d["LOOP_NUM_ID"] = session_index or 0

        d.setdefault(
            "LOOP_ID",
            sanitize_filename(str(loop_dict_item.get("LOOP_ID", "unknown"))),
        )

    if timestamp is not None:
        d["TIMESTAMP"] = timestamp

    known_placeholders = ["CHUNK_", "LOOP_", "TIMESTAMP"]
    if not any(ph in result for ph in known_placeholders):
        if session_index is not None:
            return f"session_{session_index:04d}.md"
        return "output.md"

    try:
        formatted = result.format_map(d)
    except (KeyError, ValueError):
        if session_index is not None:
            return f"session_{session_index:04d}.md"
        formatted = result

    return sanitize_filename(formatted)
