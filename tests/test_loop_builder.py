# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""Unit tests for LoopBuilder: no-file path, JSONL vs. plain-line parsing,
and the read-failure error message. The 50-item hard limit itself is
covered separately in tests/test_circuit_breakers.py::TestLoopBuilderItemLimit.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from support import blank_parameter_groups

from dragiter.application.pipeline.loop_builder import LoopBuilder, LoopBuilderError
from dragiter.domain.models.settings import ValueOrigin


def _ip(loop_path: Path | None = None):
    groups = blank_parameter_groups()
    if loop_path is not None:
        groups["ip"].loop_file_path_setting.set(loop_path, ValueOrigin.CLI)
    return groups["ip"]


def test_no_loop_file_returns_empty_loop() -> None:
    """Covers LOOP-01."""
    loop = LoopBuilder().run(_ip())

    assert loop.lines == []


def test_jsonl_object_line_becomes_its_own_keys_plus_num_id(tmp_path: Path) -> None:
    """Covers LOOP-06."""
    path = tmp_path / "loop.jsonl"
    path.write_text('{"LOOP_ID": "first", "extra": 1}\n{"LOOP_ID": "second"}\n', encoding="utf-8")

    loop = LoopBuilder().run(_ip(path))

    assert loop.lines == [
        {"LOOP_ID": "first", "extra": 1, "LOOP_NUM_ID": 1},
        {"LOOP_ID": "second", "LOOP_NUM_ID": 2},
    ]


def test_jsonl_object_num_id_overwrites_any_same_named_key(tmp_path: Path) -> None:
    """Covers LOOP-06: LOOP_NUM_ID always reflects the line's own position."""
    path = tmp_path / "loop.jsonl"
    path.write_text('{"LOOP_NUM_ID": 999}\n', encoding="utf-8")

    loop = LoopBuilder().run(_ip(path))

    assert loop.lines == [{"LOOP_NUM_ID": 1}]


@pytest.mark.parametrize(
    "line",
    [
        "plain text line",
        "42",
        "[1, 2, 3]",
        "true",
        "null",
    ],
)
def test_non_object_line_falls_back_to_loop_content(tmp_path: Path, line: str) -> None:
    """Covers LOOP-07: invalid JSON and valid-but-non-object JSON both fall back."""
    path = tmp_path / "loop.txt"
    path.write_text(line + "\n", encoding="utf-8")

    loop = LoopBuilder().run(_ip(path))

    assert loop.lines == [{"LOOP_CONTENT": line, "LOOP_NUM_ID": 1}]


def test_read_failure_names_the_loop_file_path_not_the_prompt_file_path(
    tmp_path: Path,
) -> None:
    """Covers LOOP-08.

    Regression test for a copy-paste bug: the wrapping LoopBuilderError used
    to report ip.prompt_file_path_setting.value instead of the loop file's
    own path.
    """
    missing_loop_file = tmp_path / "does-not-exist.txt"

    with pytest.raises(LoopBuilderError) as exc_info:
        LoopBuilder().run(_ip(missing_loop_file))

    message = str(exc_info.value)
    assert str(missing_loop_file) in message
