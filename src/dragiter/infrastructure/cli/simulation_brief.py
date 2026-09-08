# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from __future__ import annotations

from dataclasses import dataclass

# Four equally padded columns keep the board aligned on a console and in Markdown.
COLUMN_WIDTHS: tuple[int, int, int, int] = (16, 16, 16, 16)


@dataclass(frozen=True)
class SimulationBrief:
    """Facts for the compact simulate-mode stdout run board."""

    model: str
    sessions: int
    chunks: int
    valid_chunks: int
    source_files: int
    loop_items: int
    total_chars: int
    sequential: bool
    pack_limit_chars: int | None
    peak_tokens: int | None
    token_limit: int | None
    peak_session: int | None
    window_ok: bool | None
    warning_count: int
    output_dir: str | None
    output_file: str | None
    result_count: int


@dataclass(frozen=True)
class SimulationSessionBrief:
    """Facts for one chat session in a simulate-mode output file."""

    session_index: int
    session_count: int
    sequential: bool
    filename: str
    chunk_label: str
    section: str
    loop_label: str
    loop_line: str
    tokens: int | None


def format_simulation_brief(brief: SimulationBrief, *, frame: bool = True) -> str:
    """Default board. ``frame=True`` for the TTY box, ``False`` for GFM files."""
    return format_simulation_panel_brief(brief, frame=frame)


_ROLE_INITIAL: dict[str, str] = {
    "system": "S",
    "user": "U",
    "assistant": "A",
}


SECTION_RULE = "***"


def join_ruled_sections(*sections: str) -> str:
    """Join GFM blocks with thematic breaks so editors keep rendering tables."""

    parts = [section.strip() for section in sections if section and section.strip()]
    if not parts:
        return ""
    gap = f"\n\n{SECTION_RULE}\n\n"
    return f"{SECTION_RULE}\n\n{gap.join(parts)}\n\n{SECTION_RULE}"


def format_payload_table(messages: list[tuple[str, str | None]]) -> str:
    """Render the chat payload as a two-column GFM table."""

    rows = [("R", "Content")]
    for role, content in messages:
        rows.append((_role_initial(role), content or ""))

    role_width = max(len("R"), max((len(row[0]) for row in rows), default=1))
    lines = [
        _two_col(rows[0][0], rows[0][1], role_width),
        f"| {'-' * role_width} | --- |",
    ]
    for role, content in rows[1:]:
        lines.append(_two_col(role, content, role_width))
    return "\n".join(lines)


def format_simulation_transcript(
    messages: list[tuple[str, str | None]],
    header: str,
) -> str:
    """Render a header board and payload table, separated by thematic breaks."""

    table = format_payload_table(messages)
    if header:
        return join_ruled_sections(header, table)
    return join_ruled_sections(table)


def format_simulation_session_brief(
    brief: SimulationSessionBrief,
    *,
    frame: bool = False,
) -> str:
    """Render the per-session board used in simulate-mode output files."""

    mode = "sequential" if brief.sequential else "batched"
    tokens = _dash(brief.tokens)
    rows = [
        ("session", f"{brief.session_index} / {brief.session_count}", "mode", mode),
        ("file", brief.filename or "none", "chunk", brief.chunk_label),
        ("section", brief.section or "none", "loop", brief.loop_label),
        ("loop line", brief.loop_line or "none", "tokens", tokens),
    ]
    return _render_board(rows, frame=frame)


def _role_initial(role: str) -> str:
    key = (role or "").strip().lower()
    if key in _ROLE_INITIAL:
        return _ROLE_INITIAL[key]
    return (role[:1] or "?").upper()


def _one_line(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\n", "<br>").replace("|", "\\|")


def _two_col(role: str, content: str, role_width: int) -> str:
    return f"| {role.ljust(role_width)} | {_one_line(content)} |"


def format_simulation_panel_brief(brief: SimulationBrief, *, frame: bool = True) -> str:
    """Render the run board as a fixed-width four-column Markdown table."""

    model = brief.model or "unset"
    mode = "sequential" if brief.sequential else "batched"
    pack = "off" if brief.pack_limit_chars is None or brief.pack_limit_chars <= 0 else _count(brief.pack_limit_chars)
    window = _window_word(brief.window_ok)
    peak = _dash(brief.peak_tokens)
    limit = _dash(brief.token_limit)
    slot = _dash(brief.peak_session)
    output = _output_path(brief)

    rows = [
        ("DRAGITER", "simulate on", "api off", "config ok"),
        ("model", model, "mode", mode),
        ("sessions", str(brief.sessions), "chunks / files", f"{brief.chunks} / {brief.source_files}"),
        ("valid / loops", f"{brief.valid_chunks} / {brief.loop_items}", "chars", _count(brief.total_chars)),
        ("pack", pack, "window", window),
        ("peak / limit", f"{peak} / {limit}", "peak at / warns", f"{slot} / {brief.warning_count}"),
        ("output", output, "replies / stdout", f"{brief.result_count} / brief"),
    ]
    return _render_board(rows, frame=frame)


def _render_board(rows: list[tuple[str, ...]], *, frame: bool) -> str:
    """GFM table: header, separator, body. Optional TTY frame above and below."""

    lines: list[str] = []
    if frame:
        lines.append(_md_sep())
    lines.append(_md_row(rows[0]))
    lines.append(_md_sep())
    lines.extend(_md_row(row) for row in rows[1:])
    if frame:
        lines.append(_md_sep())
    return "\n".join(lines)


def _md_row(cells: tuple[str, ...]) -> str:
    padded = [_pad(cell, width) for cell, width in zip(cells, COLUMN_WIDTHS, strict=True)]
    return "| " + " | ".join(padded) + " |"


def _md_sep() -> str:
    dashes = ["-" * width for width in COLUMN_WIDTHS]
    return "| " + " | ".join(dashes) + " |"


def _pad(value: str, width: int) -> str:
    return _clip(value.replace("|", "\\|"), width).ljust(width)


def _output_path(brief: SimulationBrief) -> str:
    if brief.output_dir:
        return str(brief.output_dir)
    if brief.output_file:
        return str(brief.output_file)
    return "none"


def _window_word(window_ok: bool | None) -> str:
    if window_ok is True:
        return "yes"
    if window_ok is False:
        return "no"
    return "n/a"


def _dash(value: int | None) -> str:
    return "--" if value is None else _count(value)


def _count(value: int) -> str:
    return f"{value:,}"


def _clip(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."
