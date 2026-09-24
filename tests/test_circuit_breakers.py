# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Unit tests for the safety circuit breakers.

These limits protect against accidental resource exhaustion and unbounded API
cost. They must:

  * abort with a clear, actionable error when the hard limit is exceeded
  * remain invisible for normal workloads
  * emit diagnostic warnings for suboptimal chunk sizes

All tests are fully isolated (tmp_path / in-memory fakes, no network, no LLM).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dragiter.application.pipeline.loop_builder import LoopBuilder, LoopBuilderError
from dragiter.application.pipeline.material_tokenizer import (
    MaterialTokenizer,
    MaterialTokenizerError,
)
from dragiter.domain.models.parameters import ExecutionParameters
from dragiter.domain.models.resources import Resources, ResourceSection
from dragiter.domain.models.settings import (
    PackLimitCharsIntSetting,
    MaxChunksIntSetting,
    SequentialProcessingBoolSetting,
    SimulateBoolSetting,
    ValueOrigin,
)
from dragiter.domain.models.text_file import TextFile
from dragiter.domain.ports.text_file_reader import TextFileReaderError
from dragiter.infrastructure.file.simple_text_file_reader import SimpleTextFileReader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_text(exc: BaseException) -> str:
    """
    Collect the full error text including any chained cause.

    The pipeline currently wraps domain exceptions in a generic outer error
    (`from e`). Checking both layers keeps the tests stable whether or not
    that wrapping is later removed.
    """
    parts = [str(exc)]
    cause = exc.__cause__
    if cause is not None:
        parts.append(str(cause))
    return " ".join(parts)


def _make_resources_with_content(
    tmp_path: Path,
    content: str,
    *,
    section_name: str = "sec01",
    regex: str = r"(^#+\s+.*$)",
) -> Resources:
    """Build a minimal Resources object pointing at a single temp file."""
    path = tmp_path / "material.md"
    path.write_text(content, encoding="utf-8")

    section = ResourceSection(
        section_name=section_name,
        text_files=[TextFile(path=path)],
        regex_patterns=regex,
        exclude_filters=[],
        include_filters=[],
    )
    resources = Resources()
    resources.append_resource_section(section)
    return resources


def _blank_ep() -> ExecutionParameters:
    return ExecutionParameters(
        SimulateBoolSetting("simulate"),
        SequentialProcessingBoolSetting("sequential_processing"),
        PackLimitCharsIntSetting("pack_limit_chars"),
        MaxChunksIntSetting("max_chunks"),
    )


def _heading_document(
    num_sections: int, body: str = "Body text for this section."
) -> str:
    """Generate a Markdown document with exactly *num_sections* headings."""
    parts = [f"# Section {i}\n\n{body}\n" for i in range(1, num_sections + 1)]
    return "\n".join(parts)


class _FixedContentReader:
    """Minimal TextFileReader stand-in that always returns the same string."""

    def __init__(self, content: str) -> None:
        self._content = content

    def read(self, text_file: TextFile) -> str:
        return self._content


# ---------------------------------------------------------------------------
# SimpleTextFileReader - 100 MB hard limit
# ---------------------------------------------------------------------------


class TestSimpleTextFileReaderLimit:
    """100 MB per-file hard limit. Covers LIMT-08."""

    def test_small_file_is_accepted(self, tmp_path: Path) -> None:
        path = tmp_path / "ok.txt"
        path.write_text("hello world", encoding="utf-8")

        reader = SimpleTextFileReader()
        result = reader.read(TextFile(path=path))

        assert result == "hello world"

    def test_oversized_file_raises_with_clear_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "huge.txt"
        path.write_text("tiny on disk", encoding="utf-8")

        # Avoid creating a real 100 MB file: report a fake size via stat().
        fake_stat = MagicMock()
        fake_stat.st_size = SimpleTextFileReader.MAX_FILE_SIZE_BYTES + 1
        monkeypatch.setattr(Path, "stat", lambda self, *a, **k: fake_stat)

        reader = SimpleTextFileReader()
        with pytest.raises(TextFileReaderError) as exc_info:
            reader.read(TextFile(path=path))

        msg = str(exc_info.value)
        assert "100 MB" in msg
        assert "huge.txt" in msg
        assert "split" in msg.lower()

    def test_file_exactly_at_limit_is_accepted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "edge.txt"
        path.write_text("x", encoding="utf-8")

        fake_stat = MagicMock()
        fake_stat.st_size = SimpleTextFileReader.MAX_FILE_SIZE_BYTES
        monkeypatch.setattr(Path, "stat", lambda self, *a, **k: fake_stat)
        # Bypass the real read_text so we do not depend on the fake size.
        monkeypatch.setattr(Path, "read_text", lambda self, encoding="utf-8": "x")

        reader = SimpleTextFileReader()
        assert reader.read(TextFile(path=path)) == "x"


# ---------------------------------------------------------------------------
# MaterialTokenizer - 200 chunk hard limit + size warnings
# ---------------------------------------------------------------------------


class TestMaterialTokenizerChunkLimit:
    """200 total chunks hard limit. Covers LIMT-09."""

    def test_under_limit_succeeds(self, tmp_path: Path) -> None:
        content = _heading_document(MaterialTokenizer.MAX_TOTAL_CHUNKS)
        resources = _make_resources_with_content(tmp_path, content)
        tokenizer = MaterialTokenizer(text_file_reader=SimpleTextFileReader())

        material = tokenizer.run(resources, _blank_ep())

        assert len(material.chunks) == MaterialTokenizer.MAX_TOTAL_CHUNKS

    def test_over_limit_raises_with_actionable_message(self, tmp_path: Path) -> None:
        over = MaterialTokenizer.MAX_TOTAL_CHUNKS + 1
        content = _heading_document(over)
        resources = _make_resources_with_content(tmp_path, content)
        tokenizer = MaterialTokenizer(text_file_reader=SimpleTextFileReader())

        with pytest.raises(MaterialTokenizerError) as exc_info:
            tokenizer.run(resources, _blank_ep())

        msg = _error_text(exc_info.value)
        assert str(MaterialTokenizer.MAX_TOTAL_CHUNKS) in msg
        assert "refine your regex" in msg.lower() or "fewer files" in msg.lower()

    def test_limit_is_checked_across_multiple_sections(self, tmp_path: Path) -> None:
        """Chunks from successive resource sections accumulate toward the limit."""
        half = MaterialTokenizer.MAX_TOTAL_CHUNKS // 2 + 1  # two sections → over limit
        content = _heading_document(half)

        path_a = tmp_path / "a.md"
        path_b = tmp_path / "b.md"
        path_a.write_text(content, encoding="utf-8")
        path_b.write_text(content, encoding="utf-8")

        resources = Resources()
        for name, path in (("sec_a", path_a), ("sec_b", path_b)):
            resources.append_resource_section(
                ResourceSection(
                    section_name=name,
                    text_files=[TextFile(path=path)],
                    regex_patterns=r"(^#+\s+.*$)",
                    exclude_filters=[],
                    include_filters=[],
                )
            )

        tokenizer = MaterialTokenizer(text_file_reader=SimpleTextFileReader())
        with pytest.raises(MaterialTokenizerError) as exc_info:
            tokenizer.run(resources, _blank_ep())

        assert str(MaterialTokenizer.MAX_TOTAL_CHUNKS) in _error_text(exc_info.value)

    def test_max_chunks_setting_overrides_default(self, tmp_path: Path) -> None:
        """Covers LIMT-10."""
        content = _heading_document(6)
        resources = _make_resources_with_content(tmp_path, content)
        tokenizer = MaterialTokenizer(text_file_reader=SimpleTextFileReader())
        ep = _blank_ep()
        ep.max_chunks_int_setting.set(5, ValueOrigin.CLI)

        with pytest.raises(MaterialTokenizerError) as exc_info:
            tokenizer.run(resources, ep)

        msg = _error_text(exc_info.value)
        assert "5" in msg
        assert "max_chunks" in msg

        ep_ok = _blank_ep()
        ep_ok.max_chunks_int_setting.set(6, ValueOrigin.CLI)
        material = tokenizer.run(resources, ep_ok)
        assert len(material.chunks) == 6


class TestMaterialTokenizerChunkSizeWarnings:
    """Verbose INFO notes for final chunks that are too small or over budget. Covers LIMT-11."""

    def test_tiny_chunk_emits_info(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        content = "# A\nx\n# B\ny\n"
        resources = _make_resources_with_content(tmp_path, content)
        tokenizer = MaterialTokenizer(text_file_reader=SimpleTextFileReader())

        with caplog.at_level("INFO"):
            tokenizer.run(resources, _blank_ep())

        assert any("shorter than" in r.message.lower() for r in caplog.records)

    def test_oversize_chunk_emits_info_when_pack_limit_set(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        huge_body = "W" * 200
        content = f"# Big Section\n\n{huge_body}\n"
        resources = _make_resources_with_content(tmp_path, content)
        ep = _blank_ep()
        ep.pack_limit_chars_int_setting.set(80, ValueOrigin.CLI)
        tokenizer = MaterialTokenizer(text_file_reader=SimpleTextFileReader())

        with caplog.at_level("INFO"):
            tokenizer.run(resources, ep)

        assert any("exceed pack_limit_chars" in r.message.lower() for r in caplog.records)

    def test_normal_chunk_emits_no_size_info(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        body = "Normal paragraph. " * 20
        content = f"# Normal\n\n{body}\n"
        resources = _make_resources_with_content(tmp_path, content)
        tokenizer = MaterialTokenizer(text_file_reader=SimpleTextFileReader())

        with caplog.at_level("INFO"):
            tokenizer.run(resources, _blank_ep())

        size_notes = [
            r
            for r in caplog.records
            if "shorter than" in r.message.lower()
            or "exceed pack_limit_chars" in r.message.lower()
        ]
        assert size_notes == []


# ---------------------------------------------------------------------------
# LoopBuilder - 50 item hard limit
# ---------------------------------------------------------------------------


class TestLoopBuilderItemLimit:
    """50 loop-item hard limit. Covers LIMT-12."""

    def _loop_params(self, path: Path) -> InputParameters:
        from dragiter.domain.models.parameters import InputParameters
        from dragiter.domain.models.settings import (
            LoopFilePathSetting,
            PromptFilePathSetting,
            ResourceFilePathSetting,
            TaskStringSetting,
        )

        loop_setting = LoopFilePathSetting("loop_file")
        loop_setting.set(path, ValueOrigin.CLI)
        return InputParameters(
            TaskStringSetting("task"),
            PromptFilePathSetting("prompt_file"),
            loop_setting,
            ResourceFilePathSetting("resource_file"),
        )

    def test_under_limit_succeeds(self, tmp_path: Path) -> None:
        path = tmp_path / "loop.txt"
        path.write_text(
            "\n".join(f"item-{i}" for i in range(LoopBuilder.MAX_LOOP_ITEMS)),
            encoding="utf-8",
        )
        builder = LoopBuilder()

        loop = builder.run(self._loop_params(path))

        assert len(loop.lines) == LoopBuilder.MAX_LOOP_ITEMS

    def test_over_limit_raises_with_actionable_message(self, tmp_path: Path) -> None:
        """Covers LOOP-04."""
        path = tmp_path / "loop.txt"
        path.write_text(
            "\n".join(f"item-{i}" for i in range(LoopBuilder.MAX_LOOP_ITEMS + 1)),
            encoding="utf-8",
        )
        builder = LoopBuilder()

        with pytest.raises(LoopBuilderError) as exc_info:
            builder.run(self._loop_params(path))

        msg = _error_text(exc_info.value)
        assert str(LoopBuilder.MAX_LOOP_ITEMS) in msg
        assert "split" in msg.lower() or "batch" in msg.lower()

    def test_exactly_at_limit_is_accepted(self, tmp_path: Path) -> None:
        """Covers LOOP-03."""
        path = tmp_path / "loop.txt"
        path.write_text(
            "\n".join(f"item-{i}" for i in range(LoopBuilder.MAX_LOOP_ITEMS)),
            encoding="utf-8",
        )
        builder = LoopBuilder()

        loop = builder.run(self._loop_params(path))
        assert len(loop.lines) == LoopBuilder.MAX_LOOP_ITEMS

    def test_empty_lines_do_not_count_toward_limit(self, tmp_path: Path) -> None:
        """read_stripped_lines_from_file drops blank lines before the check. Covers LOOP-02."""
        path = tmp_path / "loop.txt"
        # 50 real items + many blank lines must still pass.
        lines = [f"item-{i}" for i in range(LoopBuilder.MAX_LOOP_ITEMS)]
        padded = []
        for line in lines:
            padded.append(line)
            padded.append("")
            padded.append("   ")
        path.write_text("\n".join(padded), encoding="utf-8")

        builder = LoopBuilder()
        loop = builder.run(self._loop_params(path))
        assert len(loop.lines) == LoopBuilder.MAX_LOOP_ITEMS

    def test_jsonl_items_are_subject_to_the_same_limit(self, tmp_path: Path) -> None:
        """Covers LOOP-05."""
        path = tmp_path / "loop.jsonl"
        path.write_text(
            "\n".join(f'{{"id": {i}}}' for i in range(LoopBuilder.MAX_LOOP_ITEMS + 1)),
            encoding="utf-8",
        )
        builder = LoopBuilder()

        with pytest.raises(LoopBuilderError) as exc_info:
            builder.run(self._loop_params(path))

        assert str(LoopBuilder.MAX_LOOP_ITEMS) in _error_text(exc_info.value)
