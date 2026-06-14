import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    num_id: int
    filename: str
    section_name: str
    section_num_id: int
    valid: bool
    content: str

    @property
    def formatted_content(self):
        return "=== Chunk {num_id:04d} Filename: {filename} Section: {section_name} ===\n\n{content}".format(
            num_id=self.num_id or 0,
            filename=self.filename,
            section_name=self.section_name,
            content=self.content
        )

    def format_template(self, template: str = "") -> str:
        result = template or ""
        d = {
            "CHUNK_NUM_ID": self.num_id,
            "CHUNK_FILE_NAME": self.filename,
            "CHUNK_SECTION_NAME": self.section_name,
            "CHUNK_SECTION_NUM_ID": self.section_num_id,
            "CHUNK_CONTENT": self.content
        }

        return result.format_map(d)
