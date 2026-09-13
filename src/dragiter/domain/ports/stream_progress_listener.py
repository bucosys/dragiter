# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol, runtime_checkable


@runtime_checkable
class StreamProgressListener(Protocol):
    """Progress signals emitted from the streaming completion loop."""

    def on_stream_chunk(self) -> None:
        """Called for every streamed chunk. No thread or timer."""

    def abandon_session(self) -> None:
        """Commit the live request line before a log line is written."""
