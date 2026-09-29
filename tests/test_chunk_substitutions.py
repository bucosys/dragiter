# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold
"""chunk_substitutions: literal replace after split, before filter and pack."""

from __future__ import annotations

from pathlib import Path

import pytest

from dragiter.application.pipeline.material_tokenizer import (
    MaterialTokenizer,
    MaterialTokenizerError,
)
from dragiter.application.pipeline.resource_collector import (
    MaterialCollectorError,
    ResourceCollector,
)
from dragiter.domain.models.parameters import (
    ExecutionParameters,
    InputParameters,
    WorkspaceParameters,
)
from dragiter.domain.models.resources import (
    Resources,
    ResourceSection,
    ResourceSectionError,
)
from dragiter.domain.models.settings import (
    BaseDirectoryPathSetting,
    ConfigFilePathSetting,
    LoopFilePathSetting,
    MaxChunksIntSetting,
    PackLimitCharsIntSetting,
    PromptFilePathSetting,
    ResourceFilePathSetting,
    ResumeBoolSetting,
    SequentialProcessingBoolSetting,
    SimulateBoolSetting,
    TaskStringSetting,
    ValueOrigin,
)
from dragiter.domain.models.text_file import TextFile
from dragiter.infrastructure.file.simple_text_file_reader import SimpleTextFileReader

LINE_REGEX = r"^[^\n]*\n?"


class _AcceptAllChecker:
    def detect_encoding(self, path: Path) -> str:
        return "utf-8"


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


def _tokenize(
    tmp_path: Path,
    content: str,
    *,
    name: str = "note.txt",
    regex: str | list[str] = LINE_REGEX,
    pack_limit_chars: int | None = None,
    exclude_filters: list[str] | None = None,
    include_filters: list[str] | None = None,
    chunk_substitutions: list[dict[str, str]] | None = None,
    ep: ExecutionParameters | None = None,
):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    section = ResourceSection(
        section_name="sec01",
        text_files=[TextFile(path=path)],
        regex_patterns=[regex] if isinstance(regex, str) else regex,
        exclude_filters=exclude_filters or [],
        include_filters=include_filters or [],
        pack_limit_chars=pack_limit_chars,
        chunk_substitutions=chunk_substitutions,
    )
    bag = Resources()
    bag.append_resource_section(section)
    return MaterialTokenizer(text_file_reader=SimpleTextFileReader()).run(
        bag, ep or _ep()
    )


def _collect(tmp_path: Path, body: str):
    source = tmp_path / "note.md"
    source.write_text("# hi\n", encoding="utf-8")
    resource_toml = tmp_path / "resource.toml"
    resource_toml.write_text(body, encoding="utf-8")
    res_setting = ResourceFilePathSetting("resource_file")
    res_setting.set(resource_toml, ValueOrigin.CLI)
    base_setting = BaseDirectoryPathSetting("base_directory")
    base_setting.set(tmp_path, ValueOrigin.CLI)
    ip = InputParameters(
        TaskStringSetting("task"),
        PromptFilePathSetting("prompt_file"),
        LoopFilePathSetting("loop_file"),
        res_setting,
    )
    wp = WorkspaceParameters(base_setting, ConfigFilePathSetting("config_file"))
    return ResourceCollector(_AcceptAllChecker()).run(ip, wp)


def test_absent_substitutions_leave_split_text_unchanged(tmp_path: Path) -> None:
    """Covers CHNK-15."""
    material = _tokenize(tmp_path, "a    b\n")
    assert [chunk.content for chunk in material.chunks] == ["a    b"]


def test_collapses_long_runs_of_spaces(tmp_path: Path) -> None:
    """Covers CHNK-16."""
    material = _tokenize(
        tmp_path,
        "a    b\n",
        chunk_substitutions=[{"pattern": r"[ \t]{2,}", "replacement": " "}],
    )
    assert [chunk.content for chunk in material.chunks] == ["a b"]


def test_empty_replacement_deletes_the_match(tmp_path: Path) -> None:
    """Covers CHNK-17."""
    material = _tokenize(
        tmp_path,
        "a----b\n",
        chunk_substitutions=[{"pattern": r"-+", "replacement": ""}],
    )
    assert material.chunks[0].content == "ab"


def test_second_rule_sees_first_rule_result(tmp_path: Path) -> None:
    """Covers CHNK-18."""
    material = _tokenize(
        tmp_path,
        "a----b\n",
        chunk_substitutions=[
            {"pattern": r"-+", "replacement": "  "},
            {"pattern": r"[ ]{2,}", "replacement": " "},
        ],
    )
    assert material.chunks[0].content == "a b"


def test_backslash_one_in_replacement_is_literal(tmp_path: Path) -> None:
    """Covers CHNK-19."""
    material = _tokenize(
        tmp_path,
        "ab\n",
        chunk_substitutions=[{"pattern": r"(a)(b)", "replacement": r"\1"}],
    )
    assert material.chunks[0].content == "\\1"


def test_whitespace_only_piece_is_discarded(tmp_path: Path) -> None:
    """Covers CHNK-20."""
    material = _tokenize(
        tmp_path,
        "keep\nxxxx\n",
        chunk_substitutions=[{"pattern": r"x+", "replacement": ""}],
    )
    assert [chunk.content for chunk in material.chunks] == ["keep"]


def test_invalid_pattern_names_section_and_index(tmp_path: Path) -> None:
    """Covers CHNK-21."""
    with pytest.raises(
        MaterialTokenizerError,
        match=r"Invalid chunk_substitutions\[0\] in section 'sec01'",
    ):
        _tokenize(
            tmp_path,
            "ab\n",
            chunk_substitutions=[{"pattern": "[", "replacement": " "}],
        )


def test_pack_budget_uses_substituted_length(tmp_path: Path) -> None:
    """Covers CHNK-22."""
    # After the split strip, the first piece is 12 characters so it will not
    # pack with "cccc" at limit 12. Collapsing spaces leaves 3 characters.
    raw = "a          b\ncccc\n"
    without = _tokenize(tmp_path, raw, name="raw.txt", pack_limit_chars=12, ep=_ep(12))
    assert len(without.chunks) == 2
    with_sub = _tokenize(
        tmp_path,
        raw,
        name="sub.txt",
        pack_limit_chars=12,
        ep=_ep(12),
        chunk_substitutions=[{"pattern": r"[ ]{2,}", "replacement": " "}],
    )
    assert len(with_sub.chunks) == 1
    assert with_sub.chunks[0].content == "a b" + "\n\n" + "cccc"


def test_filters_see_substituted_text(tmp_path: Path) -> None:
    """Covers CHNK-23."""
    material = _tokenize(
        tmp_path,
        "keep    x\n",
        exclude_filters=["keep x"],
        chunk_substitutions=[{"pattern": r"[ ]{2,}", "replacement": " "}],
    )
    assert material.chunks[0].content == "keep x"
    assert material.chunks[0].valid is False


def test_split_runs_on_raw_text_before_substitution(tmp_path: Path) -> None:
    """Covers CHNK-24."""
    content = "intro    text\n# Title\nbody    here\n"
    material = _tokenize(
        tmp_path,
        content,
        regex=r"^#+\s+",
        chunk_substitutions=[{"pattern": r"[ ]{2,}", "replacement": " "}],
    )
    assert len(material.chunks) == 2
    assert material.chunks[0].content == "intro text"
    assert material.chunks[1].content.startswith("# Title")
    assert "body here" in material.chunks[1].content


def test_collector_stores_and_logs_substitutions(tmp_path: Path) -> None:
    """Covers MATL-07."""
    resources = _collect(
        tmp_path,
        "\n".join(
            [
                "[config01]",
                'glob_patterns = ["*.md"]',
                f"base_directory = {str(tmp_path)!r}",
                "chunk_substitutions = [",
                '  { pattern = "[ \\\\t]{2,}", replacement = " " },',
                "]",
            ]
        )
        + "\n",
    )
    rules = resources.resource_sections[0].chunk_substitutions
    assert len(rules) == 1
    assert rules[0].pattern == r"[ \t]{2,}"
    assert rules[0].replacement == " "
    logged = resources.to_activity_dict_list()[0]["sections"][0]["chunk_substitutions"]
    assert logged == [{"pattern": r"[ \t]{2,}", "replacement": " "}]


def test_collector_rejects_entry_without_pattern(tmp_path: Path) -> None:
    """Covers MATL-08."""
    with pytest.raises(MaterialCollectorError, match="config01.*no pattern"):
        _collect(
            tmp_path,
            "\n".join(
                [
                    "[config01]",
                    'glob_patterns = ["*.md"]',
                    f"base_directory = {str(tmp_path)!r}",
                    'chunk_substitutions = [{ replacement = " " }]',
                ]
            )
            + "\n",
        )


def test_section_rejects_non_list_substitutions() -> None:
    """Covers MATL-09."""
    with pytest.raises(ResourceSectionError, match="must be a list of tables"):
        ResourceSection(
            section_name="sec01",
            text_files=[],
            exclude_filters=[],
            include_filters=[],
            chunk_substitutions="not-a-list",  # type: ignore[arg-type]
        )
