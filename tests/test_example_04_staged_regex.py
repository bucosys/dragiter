# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Lock Example 04 to the staged-overflow and chunk-cap story it advertises.

The compact requirements profile is no longer padded. The section budget
must therefore sit below the longest ``##`` chapter so pattern 2 still
runs, ``small / over`` can show leftover pieces, and a lowered
``--max-chunks`` still aborts. These tests read the shipped example
files; they do not rebuild a synthetic corpus.
"""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

import pytest

from dragiter.application.pipeline.material_tokenizer import (
    MaterialTokenizer,
    MaterialTokenizerError,
)
from dragiter.domain.models.parameters import ExecutionParameters
from dragiter.domain.models.resources import ResourceSection, Resources
from dragiter.domain.models.settings import (
    MaxChunksIntSetting,
    PackLimitCharsIntSetting,
    ResumeBoolSetting,
    SequentialProcessingBoolSetting,
    SimulateBoolSetting,
    ValueOrigin,
)
from dragiter.domain.models.text_file import TextFile
from dragiter.infrastructure.file.simple_text_file_reader import SimpleTextFileReader

EXAMPLE_DIR = (
    Path(__file__).resolve().parents[1] / "examples" / "04_staged_regex_sample"
)
PROFILE = EXAMPLE_DIR / "04_dragiter_requirements_profile.md"
RESOURCE = EXAMPLE_DIR / "04_resource_staged_regex.toml"


def _section_from_shipped_resource() -> ResourceSection:
    spec = tomllib.loads(RESOURCE.read_text(encoding="utf-8"))
    table = spec["requirements"]
    return ResourceSection(
        section_name="requirements",
        text_files=[TextFile(path=PROFILE)],
        exclude_filters=[],
        include_filters=[],
        regex_patterns=list(table["regex_patterns"]),
        pack_limit_chars=int(table["pack_limit_chars"]),
        chunk_substitutions=list(table.get("chunk_substitutions", [])),
    )


def _resources() -> Resources:
    resources = Resources()
    resources.append_resource_section(_section_from_shipped_resource())
    return resources


def _ep(*, pack_cli: int | None = None, max_chunks: int | None = None) -> ExecutionParameters:
    pack = PackLimitCharsIntSetting("pack_limit_chars")
    cap = MaxChunksIntSetting("max_chunks")
    simulate = SimulateBoolSetting("simulate")
    sequential = SequentialProcessingBoolSetting("sequential_processing")
    simulate.set(True, ValueOrigin.CLI)
    if pack_cli is not None:
        pack.set(pack_cli, ValueOrigin.CLI)
    if max_chunks is not None:
        cap.set(max_chunks, ValueOrigin.CLI)
    return ExecutionParameters(simulate, sequential, pack, cap, ResumeBoolSetting("resume"))


def test_shipped_section_budget_is_below_longest_chapter() -> None:
    spec = tomllib.loads(RESOURCE.read_text(encoding="utf-8"))
    budget = int(spec["requirements"]["pack_limit_chars"])
    text = PROFILE.read_text(encoding="utf-8")
    chapters = [part for part in text.split("\n## ") if part.strip()]
    # split drops the first heading marker except on piece 0; lengths stay comparable
    longest = max(len(part) for part in chapters)
    assert budget > 0
    assert longest > budget


def test_section_budget_applies_overflow_pattern(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Covers CHNK-25."""
    tokenizer = MaterialTokenizer(SimpleTextFileReader())
    with caplog.at_level("DEBUG"):
        packed = tokenizer.run(_resources(), _ep())
    chapter_only = tokenizer.run(_resources(), _ep(pack_cli=0))

    assert any("pattern 1/2" in record.message for record in caplog.records)
    assert any("pattern 2/2" in record.message for record in caplog.records)
    assert len(packed.chunks) != len(chapter_only.chunks)
    oversize = [
        chunk
        for chunk in packed.chunks
        if len(chunk.content) > _section_from_shipped_resource().pack_limit_chars
    ]
    assert oversize, "section budget must leave at least one oversize piece"


def test_lowered_max_chunks_aborts_on_shipped_profile() -> None:
    tokenizer = MaterialTokenizer(SimpleTextFileReader())
    packed = tokenizer.run(_resources(), _ep())
    assert len(packed.chunks) > 1
    with pytest.raises(MaterialTokenizerError, match="max_chunks"):
        tokenizer.run(_resources(), _ep(max_chunks=1))


def test_shipped_chunk_substitutions_clean_the_pasted_table() -> None:
    """Covers CHNK-15 on the shipped example: the section 5.2 table arrives
    with a Markdown separator row, padded columns and a run of blank lines;
    the resource file's ``chunk_substitutions`` must strip all of it."""
    spec = tomllib.loads(RESOURCE.read_text(encoding="utf-8"))
    assert spec["requirements"]["chunk_substitutions"], (
        "the shipped resource file must define chunk_substitutions for this "
        "test to be exercising anything"
    )

    tokenizer = MaterialTokenizer(SimpleTextFileReader())
    chapter_only = tokenizer.run(_resources(), _ep(pack_cli=0))
    chapter_5 = next(
        chunk for chunk in chapter_only.chunks if "## 5. Chunking" in chunk.content
    )

    assert "| Key | Type | Required | Notes |" in chapter_5.content  # rule 1: spaces collapsed
    assert "|---" not in chapter_5.content  # rule 2: separator row dropped
    assert "0 disables packing - and overflow" in chapter_5.content  # rule 3: dash run shortened
    assert "\n\n\n" not in chapter_5.content  # rule 4: blank-line runs collapsed
    assert not re.search(r"[ \t]{2,}", chapter_5.content), "no un-collapsed space/tab run"
