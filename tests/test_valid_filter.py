"""Tests for valid-flag evaluation in MessageBuilder and selection reporting in Material."""

from __future__ import annotations

from typing import Any

import pytest

from dragiter.application.pipeline.message_builder import MessageBuilder
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.prompt_template import PromptTemplate

# ---------------------------------------------------------------------------
# Minimal stand-ins (avoid pulling the full settings hierarchy)
# ---------------------------------------------------------------------------

class _VerboseOff:
    """Stand-in for LoggingParameters with verbose disabled."""

    class _Setting:
        value = False

    verbose_bool_setting = _Setting()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mixed_chunks() -> list[Chunk]:
    """Four chunks: two valid, two invalid."""
    return [
        Chunk(num_id=1, filename="doc.md", section_name="sec", section_num_id=1,
              valid=True, content="## 1 First chapter\nContent one."),
        Chunk(num_id=2, filename="doc.md", section_name="sec", section_num_id=2,
              valid=False, content="## 2 Second chapter\nContent two."),
        Chunk(num_id=3, filename="doc.md", section_name="sec", section_num_id=3,
              valid=True, content="## 3 Third chapter\nContent three."),
        Chunk(num_id=4, filename="doc.md", section_name="sec", section_num_id=4,
              valid=False, content="## 4 Fourth chapter\nContent four."),
    ]


@pytest.fixture
def material_mixed(mixed_chunks: list[Chunk]) -> Material:
    return Material(chunks=mixed_chunks)


@pytest.fixture
def material_all_valid(mixed_chunks: list[Chunk]) -> Material:
    for c in mixed_chunks:
        c.valid = True
    return Material(chunks=mixed_chunks)


@pytest.fixture
def material_all_invalid(mixed_chunks: list[Chunk]) -> Material:
    for c in mixed_chunks:
        c.valid = False
    return Material(chunks=mixed_chunks)


@pytest.fixture
def empty_loop() -> Loop:
    return Loop(lines=[])


@pytest.fixture
def prompt_sequential() -> PromptTemplate:
    return PromptTemplate(
        instruction="You are a precise analyst.",
        first="Here is the material:",
        material="ID: {CHUNK_NUM_ID:04d}\nCONTENT:\n{CHUNK_CONTENT}",
        synthesis="Summarise the provided material.",
        temperature=0.0,
        sequential_processing=True,
        output_filename_schema="out.txt",
        output_delimiter="\n---\n",
    )


@pytest.fixture
def prompt_batched() -> PromptTemplate:
    return PromptTemplate(
        instruction="You are a precise analyst.",
        first="Here is the material:",
        material="ID: {CHUNK_NUM_ID:04d}\nCONTENT:\n{CHUNK_CONTENT}",
        synthesis="Summarise the provided material.",
        temperature=0.0,
        sequential_processing=False,
        output_filename_schema="out.txt",
        output_delimiter="\n---\n",
    )


@pytest.fixture
def message_builder() -> MessageBuilder:
    return MessageBuilder()


# ---------------------------------------------------------------------------
# MessageBuilder – sequential mode
# ---------------------------------------------------------------------------

def test_sequential_skips_invalid_chunks(
    message_builder: MessageBuilder,
    material_mixed: Material,
    prompt_sequential: PromptTemplate,
    empty_loop: Loop,
) -> None:
    """Only valid chunks must produce a ChatSession in sequential mode."""
    sessions = message_builder.run(
        material_mixed, prompt_sequential, empty_loop, _VerboseOff()
    )

    assert len(sessions.session_list) == 2
    assert all(s.chunk is not None and s.chunk.valid for s in sessions.session_list)
    assert {s.chunk.num_id for s in sessions.session_list} == {1, 3}


def test_sequential_all_invalid_yields_empty(
    message_builder: MessageBuilder,
    material_all_invalid: Material,
    prompt_sequential: PromptTemplate,
    empty_loop: Loop,
) -> None:
    """When every chunk is invalid, no ChatSession must be created."""
    sessions = message_builder.run(
        material_all_invalid, prompt_sequential, empty_loop, _VerboseOff()
    )
    assert len(sessions.session_list) == 0


def test_sequential_all_valid_keeps_all(
    message_builder: MessageBuilder,
    material_all_valid: Material,
    prompt_sequential: PromptTemplate,
    empty_loop: Loop,
) -> None:
    """All-valid material must still produce one session per chunk."""
    sessions = message_builder.run(
        material_all_valid, prompt_sequential, empty_loop, _VerboseOff()
    )
    assert len(sessions.session_list) == 4
    assert all(s.chunk.valid for s in sessions.session_list)


# ---------------------------------------------------------------------------
# MessageBuilder – batched mode
# ---------------------------------------------------------------------------

def test_batched_injects_only_valid_chunks(
    message_builder: MessageBuilder,
    material_mixed: Material,
    prompt_batched: PromptTemplate,
    empty_loop: Loop,
) -> None:
    """In batched mode only valid chunks appear as material messages."""
    sessions = message_builder.run(
        material_mixed, prompt_batched, empty_loop, _VerboseOff()
    )

    assert len(sessions.session_list) == 1
    session = sessions.session_list[0]

    # Material messages contain the CHUNK_CONTENT placeholder expansion
    material_msgs = [
        m for m in session.input_chat_message_list
        if m.content and "CONTENT:" in m.content
    ]
    assert len(material_msgs) == 2

    # The two valid chunk IDs must be present
    joined = "\n".join(m.content or "" for m in material_msgs)
    assert "ID: 0001" in joined
    assert "ID: 0003" in joined
    assert "ID: 0002" not in joined
    assert "ID: 0004" not in joined


def test_batched_all_invalid_yields_no_material(
    message_builder: MessageBuilder,
    material_all_invalid: Material,
    prompt_batched: PromptTemplate,
    empty_loop: Loop,
) -> None:
    """All-invalid material must produce a session without any expanded chunk content.

    When no valid chunks remain, the existing fallback in ``_create_chat_session``
    injects the raw material *template*.  That is intentional legacy behaviour.
    The important guarantee is that no concrete chunk (with filled placeholders
    and real content) is present.
    """
    sessions = message_builder.run(
        material_all_invalid, prompt_batched, empty_loop, _VerboseOff()
    )
    assert len(sessions.session_list) == 1

    # Collect every user message that looks like material
    material_msgs = [
        m for m in sessions.session_list[0].input_chat_message_list
        if m.content and "CONTENT:" in m.content
    ]

    # At most the raw template may appear – never an expanded chunk
    for msg in material_msgs:
        content = msg.content or ""
        # Placeholders must still be present (i.e. not expanded)
        assert "{CHUNK_NUM_ID" in content or "{CHUNK_CONTENT}" in content
        # Concrete chapter text from the fixtures must be absent
        assert "First chapter" not in content
        assert "Second chapter" not in content
        assert "Third chapter" not in content
        assert "Fourth chapter" not in content
        # Filled numeric IDs must be absent
        assert "ID: 0001" not in content
        assert "ID: 0002" not in content
        assert "ID: 0003" not in content
        assert "ID: 0004" not in content


# ---------------------------------------------------------------------------
# Material.to_activity_dict_list – selection reporting
# ---------------------------------------------------------------------------

def test_activity_shows_selection_counts(material_mixed: Material) -> None:
    """Global activity record must expose valid/invalid counts and share."""
    records = material_mixed.to_activity_dict_list()
    global_rec: dict[str, Any] = records[0]

    assert global_rec["material_chunks_count"] == 4
    assert global_rec["material_valid_chunks_count"] == 2
    assert global_rec["material_invalid_chunks_count"] == 2
    assert global_rec["material_valid_share"] == pytest.approx(0.5)
    assert global_rec["valid_characters"] > 0
    assert global_rec["total_characters"] >= global_rec["valid_characters"]


def test_activity_file_records_contain_validity_breakdown(
    material_mixed: Material,
) -> None:
    """Per-file records must also report valid/invalid chunk counts."""
    records = material_mixed.to_activity_dict_list()
    # First record is global, subsequent records are per-file
    file_recs = records[1:]
    assert len(file_recs) >= 1

    for rec in file_recs:
        assert "num_valid_chunks" in rec
        assert "num_invalid_chunks" in rec
        assert rec["num_chunks"] == rec["num_valid_chunks"] + rec["num_invalid_chunks"]


def test_activity_all_invalid(material_all_invalid: Material) -> None:
    """Edge case: zero valid chunks must be reported correctly."""
    records = material_all_invalid.to_activity_dict_list()
    global_rec = records[0]
    assert global_rec["material_valid_chunks_count"] == 0
    assert global_rec["material_invalid_chunks_count"] == 4
    assert global_rec["material_valid_share"] == 0.0
