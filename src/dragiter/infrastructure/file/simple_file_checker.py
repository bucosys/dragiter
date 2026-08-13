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
import codecs
import logging
import pathlib
from typing import Optional, List, Union

from dragiter.domain.ports.file_checker import FileChecker, BinaryFileError, EmptyFileError

logger = logging.getLogger(__name__)


class SimpleFileChecker(FileChecker):
    """
    A concrete implementation.
    Notice: It DOES NOT inherit from FileChecker, but static type checkers
    (like mypy) will still recognize it as a valid FileChecker because it
    structurally matches the Protocol.
    """

    def __init__(self, chunk_size: int = 10240, candidates: Optional[List[str]] = None):
        self.chunk_size = chunk_size
        self.candidates = candidates or ['utf-8', 'ascii', 'cp1252', 'latin-1']

    def detect_encoding(self, path: Union[str, pathlib.Path]) -> str:
        path_obj = pathlib.Path(path)

        self._verify_file_exists_and_not_empty(path_obj)

        with path_obj.open('rb') as f:
            raw_data = f.read(self.chunk_size)

        # 1. BOM Check
        bom_encoding = self._check_bom(raw_data)
        if bom_encoding:
            return bom_encoding

        # 2. Binary Check
        if b'\x00' in raw_data:
            raise BinaryFileError(f"The file {path_obj.name} contains null bytes.")

        # 3. Waterfall
        for encoding in self.candidates:
            try:
                raw_data.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue

        raise BinaryFileError(f"Could not decode {path_obj.name} as text.")

    # --- Private Helpers ---

    def _verify_file_exists_and_not_empty(self, path_obj: pathlib.Path) -> None:
        if not path_obj.exists():
            raise FileNotFoundError(f"The file {path_obj} does not exist.")
        if path_obj.stat().st_size == 0:
            raise EmptyFileError(f"The file {path_obj.name} is entirely empty.")

    def _check_bom(self, raw_data: bytes) -> Optional[str]:
        if raw_data.startswith(codecs.BOM_UTF8): return "utf-8-sig"
        if raw_data.startswith(codecs.BOM_UTF16_LE) or raw_data.startswith(codecs.BOM_UTF16_BE): return "utf-16"
        if raw_data.startswith(codecs.BOM_UTF32_LE) or raw_data.startswith(codecs.BOM_UTF32_BE): return "utf-32"
        return None
