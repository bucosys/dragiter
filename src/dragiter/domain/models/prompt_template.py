import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    instruction: str
    first: str
    material: str
    synthesis: str
    temperature: float
    sequential_processing: bool
    output_filename_schema: str
    output_delimiter: str

    def merge_synthesis_with_loop_dict(self, loop_dict: dict) -> str:
        # validate or bail out
        if loop_dict is not None and len(loop_dict.get("LOOP_CONTENT", "")) > 0:
            # loop_content = loop_element.get("LOOP_CONTENT", "")
            return self.synthesis.format_map(loop_dict)

    def __repr__(self):
        # Das hier wird im Logger angezeigt
        return f"PromptTemplate (instruction length ='{len(self.instruction or {})}', task length ='{len(self.first or {})}')"


class PromptTemplateError(Exception):
    pass
