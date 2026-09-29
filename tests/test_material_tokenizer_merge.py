# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from __future__ import annotations

from pathlib import Path

from dragiter.application.pipeline.material_tokenizer import MaterialTokenizer
from dragiter.domain.models.parameters import ExecutionParameters
from dragiter.domain.models.resources import Resources, ResourceSection
from dragiter.domain.models.settings import (
    PackLimitCharsIntSetting,
    MaxChunksIntSetting,
    ResumeBoolSetting,
    SequentialProcessingBoolSetting,
    SimulateBoolSetting,
    ValueOrigin,
)
from dragiter.domain.models.text_file import TextFile
from dragiter.infrastructure.file.simple_text_file_reader import SimpleTextFileReader


LINE_REGEX = r"^[^\n]*\n?"


def _ep(pack_limit_chars: int | None = None) -> ExecutionParameters:
    setting = PackLimitCharsIntSetting("pack_limit_chars")
    if pack_limit_chars is not None:
        setting.set(pack_limit_chars, ValueOrigin.CLI)
    return ExecutionParameters(
        SimulateBoolSetting("simulate"),
        SequentialProcessingBoolSetting("sequential_processing"),
        setting,
        MaxChunksIntSetting("max_chunks"),
        ResumeBoolSetting("resume"),
    )


def _resources(
    tmp_path: Path,
    files: dict[str, str],
    *,
    regex: str | list[str] = LINE_REGEX,
    pack_limit_chars: int | None = None,
    exclude_filters: list[str] | None = None,
    include_filters: list[str] | None = None,
) -> Resources:
    text_files: list[TextFile] = []
    for name, content in files.items():
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        text_files.append(TextFile(path=path))
    resources = Resources()
    resources.append_resource_section(
        ResourceSection(
            section_name="sec01",
            text_files=text_files,
            regex_patterns=[regex] if isinstance(regex, str) else regex,
            exclude_filters=exclude_filters or [],
            include_filters=include_filters or [],
            pack_limit_chars=pack_limit_chars,
        )
    )
    return resources


def _run(tmp_path: Path, files: dict[str, str], ep: ExecutionParameters, **kwargs):
    tokenizer = MaterialTokenizer(text_file_reader=SimpleTextFileReader())
    return tokenizer.run(_resources(tmp_path, files, **kwargs), ep)


def test_unset_limit_does_not_merge(tmp_path: Path) -> None:
    """Covers CHNK-01."""
    material = _run(tmp_path, {"a.txt": "aaaa\nbbbb\n"}, _ep())
    assert len(material.chunks) == 2


def test_zero_limit_does_not_merge(tmp_path: Path) -> None:
    """Covers CHNK-02."""
    material = _run(tmp_path, {"a.txt": "aaaa\nbbbb\n"}, _ep(0))
    assert len(material.chunks) == 2


def test_limit_packs_consecutive_lines_in_one_file(tmp_path: Path) -> None:
    """Covers CHNK-03."""
    material = _run(tmp_path, {"a.txt": "aaaa\nbbbb\n"}, _ep(20))
    assert len(material.chunks) == 1
    assert material.chunks[0].content == "aaaa" + "\n\n" + "bbbb"


def test_limit_does_not_cut_a_single_oversized_chunk(tmp_path: Path) -> None:
    """Covers CHNK-04."""
    material = _run(tmp_path, {"a.txt": "abcdefghij\n"}, _ep(4))
    assert len(material.chunks) == 1
    assert material.chunks[0].content == "abcdefghij"


def test_does_not_merge_across_files(tmp_path: Path) -> None:
    """Covers CHNK-05."""
    material = _run(
        tmp_path,
        {"a.txt": "aaaa\n", "b.txt": "bbbb\n"},
        _ep(20),
    )
    assert len(material.chunks) == 2
    assert material.chunks[0].filename.endswith("a.txt")
    assert material.chunks[1].filename.endswith("b.txt")


def test_section_limit_applies_when_ep_unset(tmp_path: Path) -> None:
    """Covers CHNK-06."""
    material = _run(
        tmp_path,
        {"a.txt": "aaaa\nbbbb\n"},
        _ep(),
        pack_limit_chars=20,
    )
    assert len(material.chunks) == 1


def test_ep_zero_overrides_section_limit(tmp_path: Path) -> None:
    """Covers CHNK-07."""
    material = _run(
        tmp_path,
        {"a.txt": "aaaa\nbbbb\n"},
        _ep(0),
        pack_limit_chars=20,
    )
    assert len(material.chunks) == 2


def test_ep_limit_overrides_section_limit(tmp_path: Path) -> None:
    """Covers CHNK-08."""
    material = _run(
        tmp_path,
        {"a.txt": "aaaa\nbbbb\n"},
        _ep(1),
        pack_limit_chars=20,
    )
    assert len(material.chunks) == 2


def test_does_not_mix_valid_and_invalid(tmp_path: Path) -> None:
    """Covers CHNK-09."""
    material = _run(
        tmp_path,
        {"a.txt": "keep\nDROP\nkeep\n"},
        _ep(50),
        exclude_filters=["DROP"],
    )
    assert [c.valid for c in material.chunks] == [True, False, True]
    assert [c.content for c in material.chunks] == ["keep", "DROP", "keep"]


def test_renumbers_after_pack(tmp_path: Path) -> None:
    """Covers CHNK-10."""
    material = _run(tmp_path, {"a.txt": "aaaa\nbbbb\n"}, _ep(20))
    assert material.chunks[0].num_id == 1
    assert material.chunks[0].section_num_id == 1


def test_split_keeps_delimiter_without_capturing_group(tmp_path: Path) -> None:
    """Covers CHNK-11."""
    material = _run(
        tmp_path,
        {"a.md": "# one\nbody-one\n# two\nbody-two\n"},
        _ep(),
        regex=r"^#+\s+.*$",
    )
    assert [chunk.content for chunk in material.chunks] == [
        "# one\nbody-one",
        "# two\nbody-two",
    ]


def test_overflow_patterns_apply_only_when_over_limit(tmp_path: Path) -> None:
    """Covers CHNK-12."""
    body = "# title\n\npara-one\n\npara-two"
    material = _run(
        tmp_path,
        {"a.md": body},
        _ep(12),
        regex=[r"^#+\s+.*$", r"\n\n"],
    )
    assert [chunk.content for chunk in material.chunks] == [
        "# title",
        "para-one",
        "para-two",
    ]


def test_overflow_patterns_are_skipped_without_limit(tmp_path: Path) -> None:
    """Covers CHNK-13."""
    body = "# title\n\npara-one\n\npara-two"
    material = _run(
        tmp_path,
        {"a.md": body},
        _ep(),
        regex=[r"^#+\s+.*$", r"\n\n"],
    )
    assert [chunk.content for chunk in material.chunks] == [body]


def test_overflow_patterns_are_skipped_when_under_limit(tmp_path: Path) -> None:
    """Covers CHNK-14."""
    body = "# title\n\npara-one\n\npara-two"
    material = _run(
        tmp_path,
        {"a.md": body},
        _ep(200),
        regex=[r"^#+\s+.*$", r"\n\n"],
    )
    assert [chunk.content for chunk in material.chunks] == [body]
