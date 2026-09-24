# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""Unit tests for BufferedActivityLogger/FileActivityLogger, masking, and the
exception record. Covers AUDT-06 through AUDT-14."""

from __future__ import annotations

import json
from typing import Any

from support import blank_parameter_groups

from dragiter.application.core.xdi import ApplicationManager
from dragiter.domain.models.settings import ValueOrigin
from dragiter.infrastructure.checksum.basic_checksum_generator import (
    BasicChecksumGenerator,
)
from dragiter.infrastructure.logging.buffered_activity_logger import (
    BufferedActivityLogger,
)
from dragiter.infrastructure.logging.file_activity_logger import FileActivityLogger


class _FlatProvider:
    """Minimal ActivityProvider double, one record per call."""

    def __init__(self, record: dict[str, Any]) -> None:
        self._record = record

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        return [self._record]


def test_seed_record_shape() -> None:
    """Covers AUDT-06."""
    for logger in (BufferedActivityLogger(), FileActivityLogger()):
        assert len(logger.activity_dict_list) == 1
        seed = logger.activity_dict_list[0]
        assert set(seed.keys()) == {"TS", "RT", "initial_status_message"}


class _RecordingLogger:
    def __init__(self) -> None:
        self.received: list[Any] = []

    def write_activity(self, activity_provider: Any) -> int:
        self.received.append(activity_provider)
        return 1

    def write_exception(self, e: Exception) -> int:
        return 1


def test_application_manager_provide_forwards_exact_object() -> None:
    """Covers AUDT-07."""
    recording_logger = _RecordingLogger()
    app = ApplicationManager(BasicChecksumGenerator(), recording_logger)
    groups = blank_parameter_groups()

    app.provide(worker=object(), data=groups["aisp"])

    assert recording_logger.received == [groups["aisp"]]
    assert recording_logger.received[0] is groups["aisp"]


def test_no_activity_file_discards_buffer() -> None:
    """Covers AUDT-08."""
    logger = FileActivityLogger()
    groups = blank_parameter_groups()  # activity_file_path_setting left unset -> value None

    logger.write_activity(groups["lp"])

    assert logger.activity_dict_list == []
    assert logger.activity_file_found is True
    assert logger.activity_file_path is None

    # Everything logged afterwards keeps being discarded, no file ever appears.
    logger.write_activity(_FlatProvider({"x": 1}))
    assert logger.activity_dict_list == []


def test_activity_file_path_flushes_accumulated_buffer(tmp_path) -> None:
    """Covers AUDT-09."""
    path = tmp_path / "activity.jsonl"
    logger = FileActivityLogger()
    seed_count = len(logger.activity_dict_list)
    groups = blank_parameter_groups()
    groups["lp"].activity_file_path_setting.set(path, ValueOrigin.CLI)

    logger.write_activity(groups["lp"])

    assert logger.activity_dict_list == []
    assert path.exists()
    lines = path.read_text(encoding="utf-8").splitlines()
    # seed record + the LoggingParameters record itself.
    assert len(lines) == seed_count + 1
    for line in lines:
        json.loads(line)  # every record round-trips as one JSON object per line


def test_further_writes_append_without_rechecking(tmp_path) -> None:
    """Covers AUDT-10."""
    path = tmp_path / "activity.jsonl"
    logger = FileActivityLogger()
    groups = blank_parameter_groups()
    groups["lp"].activity_file_path_setting.set(path, ValueOrigin.CLI)
    logger.write_activity(groups["lp"])
    lines_after_first_sync = len(path.read_text(encoding="utf-8").splitlines())

    logger.write_activity(_FlatProvider({"y": 2}))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == lines_after_first_sync + 1
    assert logger.activity_dict_list == []
    # Path stays resolved; a further write does not re-scan for "activity_file".
    assert logger.activity_file_path == path


def test_api_key_setting_is_masked() -> None:
    """Covers AUDT-11."""
    groups = blank_parameter_groups()
    groups["aisp"].api_key_string_setting.set("super-secret-value", ValueOrigin.CLI)

    [record] = groups["aisp"].to_activity_dict_list()

    assert record["api_key"] == "***MASKED***"
    assert "super-secret-value" not in record.values()


def test_non_key_setting_is_emitted_unmasked() -> None:
    """Covers AUDT-12."""
    groups = blank_parameter_groups()
    groups["aisp"].model_name_string_setting.set("qwen3:8b", ValueOrigin.CLI)

    [record] = groups["aisp"].to_activity_dict_list()

    assert record["model_name"] == "qwen3:8b"


def test_write_exception_records_live_traceback_frame() -> None:
    """Covers AUDT-13."""
    logger = BufferedActivityLogger()

    def _raise() -> None:
        raise ValueError("boom")

    try:
        _raise()
    except ValueError as e:
        logger.write_exception(e)
        expected_lineno = e.__traceback__.tb_next.tb_lineno  # type: ignore[union-attr]

    record = logger.activity_dict_list[-1]
    assert record["RT"] == "Exception"
    assert record["type"] == "ValueError"
    assert record["message"] == "boom"
    assert record["module"] == "builtins"  # type(e).__module__ for a built-in ValueError
    assert record["filename"] == __file__
    assert record["lineno"] == expected_lineno
    assert record["location"] is not None


def test_write_exception_without_traceback_leaves_frame_fields_none() -> None:
    """Covers AUDT-14."""
    logger = BufferedActivityLogger()
    e = ValueError("never raised")
    assert e.__traceback__ is None

    logger.write_exception(e)

    record = logger.activity_dict_list[-1]
    assert record["filename"] is None
    assert record["lineno"] is None
    assert record["location"] is None
