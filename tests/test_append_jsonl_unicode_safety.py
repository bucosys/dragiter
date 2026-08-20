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
Unit tests for append_jsonl_to_file Unicode / JSONL line integrity.

json.dumps(..., ensure_ascii=False) does not escape:
  - U+0085  NEXT LINE (NEL)
  - U+2028  LINE SEPARATOR
  - U+2029  PARAGRAPH SEPARATOR

These characters act as line breaks. When written into a JSONL file they
split a single JSON object across multiple physical lines and break
line-oriented consumers (splitlines + json.loads).

Regression context: stress test 2026-08-13.
"""

import json
from pathlib import Path

import pytest

from dragiter.infrastructure.io.io_services import append_jsonl_to_file

# Characters that must not appear unescaped in a JSONL line
LINE_BREAKING_CHARS = (
    "\u0085",  # NEXT LINE (NEL)
    "\u2028",  # LINE SEPARATOR
    "\u2029",  # PARAGRAPH SEPARATOR
)


def _read_jsonl_lines(path: Path) -> list[str]:
    """Read file as text and split into physical lines (no strip of content)."""
    return path.read_text(encoding="utf-8").splitlines()


def _load_jsonl_records(path: Path) -> list[dict]:
    """Parse every non-empty physical line as JSON. Raises on broken lines."""
    records = []
    for i, line in enumerate(_read_jsonl_lines(path), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise AssertionError(
                f"Line {i} is not valid JSON (JSONL integrity broken): {e}\n"
                f"Line content (repr): {line!r}"
            ) from e
    return records


# ---------------------------------------------------------------------------
# Core safety tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("evil_char,name", [
    ("\u0085", "NEL (U+0085)"),
    ("\u2028", "LINE SEPARATOR (U+2028)"),
    ("\u2029", "PARAGRAPH SEPARATOR (U+2029)"),
])
def test_jsonl_survives_unicode_line_separators(tmp_path, evil_char, name):
    """
    A single activity record whose content contains a Unicode line separator
    must still produce exactly one physical JSONL line that round-trips.
    """
    path = tmp_path / "activity.jsonl"
    original_content = f"before{evil_char}after 🚀 日本語"

    records = [
        {
            "RT": "ChatSessions",
            "session_index": 1,
            "role": "user",
            "content": original_content,
        }
    ]

    append_jsonl_to_file(path, records)

    physical_lines = _read_jsonl_lines(path)
    assert len(physical_lines) == 1, (
        f"Expected 1 physical line for content with {name}, "
        f"got {len(physical_lines)}. JSONL line integrity is broken."
    )

    loaded = _load_jsonl_records(path)
    assert len(loaded) == 1
    assert loaded[0]["content"] == original_content, (
        f"Content with {name} was not recovered losslessly"
    )


def test_jsonl_survives_all_line_separators_together(tmp_path):
    """All three dangerous characters in one payload must stay on one line."""
    path = tmp_path / "activity.jsonl"
    original = "A\u0085B\u2028C\u2029D"

    append_jsonl_to_file(path, [{"content": original, "role": "user"}])

    physical_lines = _read_jsonl_lines(path)
    assert len(physical_lines) == 1

    loaded = _load_jsonl_records(path)
    assert loaded[0]["content"] == original


def test_jsonl_multiple_records_with_evil_content(tmp_path):
    """Several records, each containing line separators, stay one-per-line."""
    path = tmp_path / "activity.jsonl"

    records = [
        {"idx": 1, "content": "one\u0085two"},
        {"idx": 2, "content": "three\u2028four"},
        {"idx": 3, "content": "five\u2029six"},
        {"idx": 4, "content": "harmless ascii only"},
    ]

    append_jsonl_to_file(path, records)

    physical_lines = _read_jsonl_lines(path)
    assert len(physical_lines) == 4

    loaded = _load_jsonl_records(path)
    assert len(loaded) == 4
    for expected, actual in zip(records, loaded):
        assert actual["content"] == expected["content"]
        assert actual["idx"] == expected["idx"]


def test_jsonl_append_preserves_previous_lines(tmp_path):
    """Appending a second batch must not corrupt earlier lines."""
    path = tmp_path / "activity.jsonl"

    append_jsonl_to_file(path, [{"batch": 1, "content": "first\u0085line"}])
    append_jsonl_to_file(path, [{"batch": 2, "content": "second\u2028line"}])

    physical_lines = _read_jsonl_lines(path)
    assert len(physical_lines) == 2

    loaded = _load_jsonl_records(path)
    assert loaded[0]["batch"] == 1
    assert loaded[0]["content"] == "first\u0085line"
    assert loaded[1]["batch"] == 2
    assert loaded[1]["content"] == "second\u2028line"


def test_jsonl_normal_unicode_still_readable(tmp_path):
    """Ordinary Unicode (emoji, CJK, umlauts) must remain unescaped/readable."""
    path = tmp_path / "activity.jsonl"
    original = "Hallo 🚀 日本語 ÄÖÜ"

    append_jsonl_to_file(path, [{"content": original}])

    raw = path.read_text(encoding="utf-8")
    # ensure_ascii=False keeps these characters visible in the file
    assert "🚀" in raw
    assert "日本語" in raw
    assert "ÄÖÜ" in raw

    loaded = _load_jsonl_records(path)
    assert loaded[0]["content"] == original


def test_jsonl_physical_line_contains_no_raw_line_separators(tmp_path):
    """
    After writing, no physical line may contain a raw U+0085 / U+2028 / U+2029.
    They must appear only as escaped \\uXXXX sequences inside the JSON string.
    """
    path = tmp_path / "activity.jsonl"
    payload = "x\u0085y\u2028z\u2029w"

    append_jsonl_to_file(path, [{"content": payload}])

    for line in _read_jsonl_lines(path):
        for ch in LINE_BREAKING_CHARS:
            assert ch not in line, (
                f"Raw {ch!r} found in physical JSONL line - "
                f"must be escaped as \\\\uXXXX"
            )

    # Round-trip still recovers the original characters
    loaded = _load_jsonl_records(path)
    assert loaded[0]["content"] == payload
