# =============================================================================
# dragiter - Deterministic Context Iterator
# Copyright (c) 2026 Michael Buchold <michael.buchold@dragiter.app>
#
# This file is part of dragiter.
#
# dragiter is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dragiter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with dragiter. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing (closed-source use, SaaS, etc.), please contact:
# Michael Buchold <michael.buchold@dragiter.app>
# =============================================================================

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

    # 100 MB Hard Limit für Textdateien
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
