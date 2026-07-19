from typing import Optional, Any

from dragiter.domain.models.chunk import Chunk
from dragiter.infrastructure.io.filename_utils import sanitize_filename


def _format_filename(
            self,
            chunk: Optional[Chunk] = None,
            loop_dict_item: Optional[dict[str, Any]] = None,
            session_index: Optional[int] = None,
            template: str = ""
    ) -> str:
        """
        Formats a filename using the provided template.

        All user-controlled values are sanitised. Format specifiers
        (like :03d) are only applied to numeric values.
        """
        result = template or ""
        d: dict[str, Any] = {}

        # --- Chunk data (sanitised) ---
        if chunk:
            d["CHUNK_NUM_ID"] = chunk.num_id if chunk.num_id is not None else 0
            d["CHUNK_FILE_NAME"] = sanitize_filename(chunk.filename or "file")
            d["CHUNK_SECTION_NAME"] = sanitize_filename(chunk.section_name or "section")
            d["CHUNK_SECTION_NUM_ID"] = chunk.section_num_id if chunk.section_num_id is not None else 0

        # --- Loop data (sanitised) ---
        if loop_dict_item:
            for key, value in loop_dict_item.items():
                if isinstance(value, (int, float)):
                    d[key] = value  # numeric → format spec allowed
                else:
                    d[key] = sanitize_filename(str(value))

            # Special handling for common keys
            d.setdefault("LOOP_NUM_ID", 0)
            d.setdefault("LOOP_ID", sanitize_filename(str(loop_dict_item.get("LOOP_ID", "UNKNOWN"))))

        # --- Timestamp ---
        d["TIMESTAMP"] = self._get_sortable_timestamp()

        # === Fallback logic ===
        known_placeholders = ["CHUNK_", "LOOP_", "TIMESTAMP"]
        has_known_placeholder = any(ph in result for ph in known_placeholders)

        if not has_known_placeholder:
            if session_index is not None:
                return f"session_{session_index:04d}.md"
            else:
                return "output.md"

        try:
            formatted = result.format_map(d)
        except (KeyError, ValueError):
            # Unknown placeholder or format spec error → fallback
            if session_index is not None:
                return f"session_{session_index:04d}.md"
            formatted = result

        return sanitize_filename(formatted)