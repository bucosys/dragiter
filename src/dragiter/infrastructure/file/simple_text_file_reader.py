# --- Concrete Implementation ---
import logging

from dragiter.domain.models.text_file import TextFile
from dragiter.domain.ports.text_file_reader import TextFileReader

logger = logging.getLogger(__name__)


class SimpleTextFileReader(TextFileReader):
    """
    A concrete implementation.
    Notice: It DOES NOT inherit from TextFileReader, but static type checkers
    (like mypy) will still recognize it as a valid TextFileReader because it
    structurally matches the Protocol.
    """

    def read(self, text_file: TextFile) -> str:
        return text_file.path.read_text(encoding=text_file.encoding)
