# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

# --- Concrete Implementation ---
import logging

from dragiter.domain.models.text_file import TextFile
from dragiter.domain.ports.text_file_reader import TextFileReader, TextFileReaderError

logger = logging.getLogger(__name__)


class SimpleTextFileReader(TextFileReader):
    """
    A concrete implementation.
    Notice: It DOES NOT inherit from TextFileReader, but static type checkers
    (like mypy) will still recognize it as a valid TextFileReader because it
    structurally matches the Protocol.
    """

    # 100 MB hard limit for text files
    MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024

    def read(self, text_file: TextFile) -> str:
        # CIRCUIT BREAKER:
        file_size = text_file.path.stat().st_size
        if file_size > self.MAX_FILE_SIZE_BYTES:
            raise TextFileReaderError(
                f"File {text_file.path.name} exceeds the maximum allowed size of 100 MB. "
                f"Please split your input files."
            )

        return text_file.path.read_text(encoding=text_file.encoding)
