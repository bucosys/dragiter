"""
Security tests for filename sanitisation and path-containment checks.

These tests verify that user-controlled or material-derived values cannot
be used to perform path-traversal attacks or to create illegal file names
when they are interpolated into output_filename_schema.
"""

from pathlib import Path

import pytest
from support import RecordingCommitService

from dragiter.application.pipeline.output_writer import OutputWriter
from dragiter.domain.models.chunk import Chunk
from dragiter.infrastructure.cli.markdown_result_board import MarkdownResultBoard
from dragiter.infrastructure.io.filename_utils import (
    ensure_path_within_directory,
    sanitize_filename,
)

# ---------------------------------------------------------------------------
# Unit tests for sanitize_filename
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected_contains, must_not_contain",
    [
        # Classic path traversal
        ("../../etc/passwd", "etc_passwd", ["../", "..\\", "/"]),
        ("..\\..\\windows\\system32", "windows_system32", ["../", "..\\", "\\"]),
        # Absolute paths
        ("/etc/shadow", "etc_shadow", ["/"]),
        ("C:\\Windows\\System32\\config", "C_Windows_System32_config", ["\\", ":"]),
        # Control characters and reserved symbols
        ("file\x00name.txt", "file_name.txt", ["\x00"]),
        ("report<>:\"|?*.md", "report_.md", ["<", ">", ":", '"', "|", "?", "*"]),
        # Empty / whitespace
        ("", "output", []),
        ("   ", "output", []),
        ("...", "output", []),
        # Normal safe names (should survive almost unchanged)
        ("security_audit_report.md", "security_audit_report.md", []),
        ("session_0001.md", "session_0001.md", []),
    ],
)
def test_sanitize_filename_blocks_traversal_and_illegal_chars(
    raw: str, expected_contains: str, must_not_contain: list[str]
):
    """OUTP-04."""
    result = sanitize_filename(raw)

    # Must never contain path separators or parent references
    assert "/" not in result
    assert "\\" not in result
    assert ".." not in result

    for forbidden in must_not_contain:
        assert forbidden not in result

    # The sanitised name should still be recognisable
    assert expected_contains in result or result == "output"


def test_sanitize_filename_truncates_long_names():
    """OUTP-05."""
    long_name = "a" * 300 + ".md"
    result = sanitize_filename(long_name, max_length=50)
    assert len(result) <= 50
    assert result.endswith(".md")


def test_sanitize_filename_fallback():
    """OUTP-06."""
    assert sanitize_filename(None) == "output"
    assert sanitize_filename("") == "output"
    assert sanitize_filename("   ") == "output"


# ---------------------------------------------------------------------------
# Unit tests for ensure_path_within_directory
# ---------------------------------------------------------------------------

def test_ensure_path_within_directory_accepts_safe_path(tmp_path: Path):
    """OUTP-07."""
    base = tmp_path / "out"
    base.mkdir()
    candidate = base / "report.md"

    resolved = ensure_path_within_directory(candidate, base)
    assert resolved == candidate.resolve()
    assert resolved.is_relative_to(base.resolve())


def test_ensure_path_within_directory_rejects_traversal(tmp_path: Path):
    """OUTP-07."""
    base = tmp_path / "out"
    base.mkdir()
    # Attempt to escape via parent directory
    candidate = base / ".." / "secret.txt"

    with pytest.raises(ValueError, match="Path traversal detected"):
        ensure_path_within_directory(candidate, base)


def test_ensure_path_within_directory_rejects_absolute_escape(tmp_path: Path):
    """OUTP-07."""
    base = tmp_path / "out"
    base.mkdir()
    # Absolute path outside base
    candidate = Path("/tmp/evil.txt")

    with pytest.raises(ValueError, match="Path traversal detected"):
        ensure_path_within_directory(candidate, base)


# ---------------------------------------------------------------------------
# Integration-style tests for OutputWriter._format_filename
# ---------------------------------------------------------------------------

def test_format_filename_sanitises_chunk_filename():
    """OUTP-02."""
    writer = OutputWriter(MarkdownResultBoard(), RecordingCommitService())
    chunk = Chunk(
        num_id=1,
        filename="../../etc/passwd",
        section_name="evil section",
        section_num_id=0,
        valid=True,
        content="dummy",
    )

    result = writer._format_filename(
        chunk=chunk,
        session_index=1,
        template="{CHUNK_FILE_NAME}_{CHUNK_NUM_ID:04d}.md",
    )

    assert "/" not in result
    assert "\\" not in result
    assert ".." not in result
    assert result.endswith(".md")
    # The dangerous parts must have been neutralised
    assert "etc_passwd" in result or "passwd" in result


def test_format_filename_sanitises_loop_values():
    """OUTP-03."""
    writer = OutputWriter(MarkdownResultBoard(), RecordingCommitService())
    loop_item = {
        "LOOP_ID": "../../../tmp/evil",
        "platform": "Instagram/../secret",
    }

    result = writer._format_filename(
        loop_dict_item=loop_item,
        session_index=1,
        template="{LOOP_ID}_{platform}.md",
    )

    assert "/" not in result
    assert "\\" not in result
    assert ".." not in result
    assert result.endswith(".md")


def test_format_filename_fallback_when_no_placeholders():
    """OUTP-01."""
    writer = OutputWriter(MarkdownResultBoard(), RecordingCommitService())
    result = writer._format_filename(session_index=7, template="plain_name")
    assert result == "session_0007.md"
