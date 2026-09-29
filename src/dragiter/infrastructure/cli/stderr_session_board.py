# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from __future__ import annotations

from pathlib import Path
import time
from typing import TextIO

from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.chat_sessions import ChatSession

START_MARK = "\N{WHITE RIGHT-POINTING TRIANGLE}" # "▶"
END_MARK = "\N{WHITE SQUARE}" # "■"
# Quadrant blocks from the same geometric family as END_MARK.
# One terminal cell; not emoji presentation.
PULSE_MARKS = "◷◶◵◴"
INTERVAL_SECONDS = 10.0


class StderrSessionBoard:
    """Labelled run board on stderr. One pulse mark, swapped on stream chunks."""

    def __init__(self, stream: TextIO, *, interactive: bool) -> None:
        # Stream and terminal mode are chosen at the composition root
        # (ADR-0000, rules 2, 3 and 5); the board only renders.
        self._stream = stream
        self._interactive = interactive
        self._watch_index = 0
        self._last_pulse = 0.0
        self._line_open = False
        self._body = ""

    def begin_run(self, *, model: str, sessions: int, simulate: bool, **facts: object) -> None:
        live = "simulate" if simulate else "live"
        api = "api off" if simulate else "api on"
        sequential = bool(facts.get("sequential"))
        mode = "sequential" if sequential else "batched"
        chunks = int(facts.get("chunks") or 0)
        source_files = int(facts.get("source_files") or 0)
        valid_chunks = int(facts.get("valid_chunks") or 0)
        loop_items = int(facts.get("loop_items") or 0)
        total_chars = int(facts.get("total_chars") or 0)
        pack_limit = facts.get("pack_limit_chars")
        pack_from = str(facts.get("pack_from") or "off")
        if isinstance(pack_limit, int) and pack_limit > 0:
            pack = f"{pack_limit:,} ({pack_from})"
        else:
            pack = "off"
        window_ok = facts.get("window_ok")
        if window_ok is True:
            window = "yes"
        elif window_ok is False:
            window = "no"
        else:
            window = "n/a"
        peak_tokens = facts.get("peak_tokens")
        token_limit = facts.get("token_limit")
        peak_session = facts.get("peak_session")
        peak = f"{peak_tokens:,}" if isinstance(peak_tokens, int) else "--"
        limit = f"{token_limit:,}" if isinstance(token_limit, int) else "--"
        peak_at = str(peak_session) if isinstance(peak_session, int) else "--"
        warning_count = int(facts.get("warning_count") or 0)
        output = str(facts.get("output") or "none")
        if len(output) > 42:
            output = output[:39] + "..."
        for line in (
            f"dragiter {live}    model {model or 'unset'}    {api}    {mode}",
            f"sessions {sessions}    chunks {chunks} / {source_files} files    "
            f"valid {valid_chunks}    loops {loop_items}",
            f"chars {total_chars:,}    pack {pack}",
            f"window {window}    peak {peak} / {limit}    peak at {peak_at}    "
            f"warns {warning_count}",
            f"output {output}",
        ):
            self._stream.write(f"{START_MARK} {line}\n")
        self._stream.flush()

    def begin_session(self, index: int, total: int, session: ChatSession) -> None:
        self._watch_index = 0
        self._last_pulse = time.monotonic()
        self._body = f"{index}/{total}  {self._session_label(session)}"
        self._line_open = True
        self._write_live(PULSE_MARKS[0])

    def on_stream_chunk(self) -> None:
        if not self._line_open:
            return
        now = time.monotonic()
        if now - self._last_pulse < INTERVAL_SECONDS:
            return
        self._last_pulse = now
        self._watch_index = (self._watch_index + 1) % len(PULSE_MARKS)
        self._write_live(PULSE_MARKS[self._watch_index])

    def abandon_session(self) -> None:
        if not self._line_open:
            return
        if self._interactive:
            self._stream.write("\n")
            self._stream.flush()
        self._line_open = False

    def end_session(self, result: ChatResult) -> None:
        duration = ""
        if result.duration_ms is not None:
            duration = f"  {result.duration_ms / 1000:.1f}s"
        reason = f"  {result.finish_reason}" if result.finish_reason else ""
        tokens = ""
        if result.input_tokens is not None or result.output_tokens is not None:
            tokens = f"  in={result.input_tokens or 0} out={result.output_tokens or 0}"
        line = f"{PULSE_MARKS[self._watch_index]} {self._body}{duration}{reason}{tokens}"
        if self._interactive and self._line_open:
            self._stream.write("\r" + line + "\033[K\n")
        else:
            self._stream.write(line + "\n")
        self._stream.flush()
        self._line_open = False

    def end_run(self, results: ChatResults) -> None:
        count = len(results.chat_result_list)
        tokens_in = sum(item.input_tokens or 0 for item in results.chat_result_list)
        tokens_out = sum(item.output_tokens or 0 for item in results.chat_result_list)
        duration_ms = sum(item.duration_ms or 0 for item in results.chat_result_list)
        reused = sum(1 for item in results.chat_result_list if item.finish_reason == "reused")
        reused_note = f"    ({reused} reused)" if reused else ""
        for line in (
            f"done {count} replies    {duration_ms / 1000:.1f}s{reused_note}",
            f"tokens in={tokens_in} out={tokens_out}",
        ):
            self._stream.write(f"{END_MARK} {line}\n")
        self._stream.flush()

    def _write_live(self, watch: str) -> None:
        line = f"{watch} {self._body}"
        if self._interactive:
            self._stream.write("\r" + line + "\033[K")
            self._stream.flush()

    @staticmethod
    def _session_label(session: ChatSession) -> str:
        chunk = session.chunk
        if chunk is None:
            return "session"
        name = Path(chunk.filename).name if chunk.filename else "chunk"
        section = chunk.section_name or "section"
        return f"{section}  {name}"
