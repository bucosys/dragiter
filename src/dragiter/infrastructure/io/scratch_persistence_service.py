# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from __future__ import annotations

import logging
from pathlib import Path

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import OutputParameters
from dragiter.infrastructure.io.filename_utils import sanitize_filename

logger = logging.getLogger(__name__)

SCRATCH_DIR_NAME = ".dragiter-partial"


class ScratchPersistenceService:
    """Append-safe per-session files under ``.dragiter-partial``."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    @classmethod
    def from_output_parameters(cls, op: OutputParameters | None) -> ScratchPersistenceService:
        root = Path.cwd()
        if op is not None and op.output_directory_path_setting.is_set:
            root = Path(op.output_directory_path_setting.value)
        elif op is not None and op.output_file_path_setting.is_set:
            root = Path(op.output_file_path_setting.value).parent
        return cls(root / SCRATCH_DIR_NAME)

    def persist(self, index: int, session: ChatSession, result: ChatResult) -> None:
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            label = "session"
            if session.chunk is not None and session.chunk.filename:
                label = Path(session.chunk.filename).stem
            name = sanitize_filename(f"session_{index:04d}_{label}.txt")
            path = self._directory / name
            content = result.output_chat_message.content or ""
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(content, encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            logger.warning("Could not persist session %s: %s", index, exc)
