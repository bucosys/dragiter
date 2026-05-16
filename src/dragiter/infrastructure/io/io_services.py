import json
import logging
import os
import tomllib
from pathlib import Path

logger = logging.getLogger(__name__)


def read_from_toml(file_path: Path, partial_dict: dict | None = None) -> dict:
    """
    Loads a TOML file. If partial_dict is provided, it updates it with the loaded content.
    Returns the loaded dictionary.
    """
    try:
        with file_path.open(mode="rb") as f:
            content = tomllib.load(f)
            if partial_dict is not None:
                partial_dict.update(content)

        logger.debug(f"Successfully initialised settings from {file_path.name}.")
        return content

    except Exception as e:
        raise IOServiceError(f"Failed to load TOML content: {file_path.name}.") from e


def read_from_jsonl(file_path: Path) -> list[dict]:
    """
    Reads a .jsonl file and returns a list of dictionaries.
    """
    result_list = []

    try:
        with file_path.open(mode="r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data_record = json.loads(line)
                    result_list.append(data_record)

        logger.debug(f"{len(result_list)} entries loaded from {file_path.name}.")

    except Exception as e:
        raise IOServiceError(f"Failed to load JSONL content: {file_path.name}.") from e

    return result_list

def read_stripped_lines_from_file(file_path: Path) -> list[str]:
    """
    Reads a .jsonl file and returns a list of dictionaries.
    """
    result_list = []

    try:
        with file_path.open(mode="r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    result_list.append(line)

        logger.debug(f"{len(result_list)} entries read from {file_path.name}.")

    except Exception as e:
        raise IOServiceError(f"Failed to load file content: {file_path.name}.") from e

    return result_list


def write_lines_to_unique_file(file_path: Path, overwrite: bool, lines: list[str]) -> os.stat_result:
    if file_path.exists() or (not overwrite):
        raise IOServiceError(f"File already exists: {file_path.name}.")

    temp_path = file_path.with_suffix(f".tmp_{os.getpid()}")

    try:
        with temp_path.open(mode="xt", encoding="utf-8") as f:
            for line in lines:
                f.write(f"{line.strip()}\n")

            # paranoid
            f.flush()
            os.fsync(f.fileno())

        # atomic swap
        os.replace(temp_path, file_path)

        logger.debug(f"{len(lines)} entries written to {file_path}.")

        return file_path.stat()     # ---> return file stat info

    except Exception as e:
        raise IOServiceError(f"Failed to write file content: {file_path}.") from e




def append_jsonl_to_file(file_path: Path, lines: list[dict]) -> os.stat_result:

    debug_string = "Appended" if file_path.exists() else "Write"

    try:
        with file_path.open(mode="a", encoding="utf-8") as f:
            for line in lines:
                jsonl = json.dumps(line, ensure_ascii=False)
                f.write(jsonl + "\n")

            # paranoid
            f.flush()
            os.fsync(f.fileno())

        logger.debug(f"{debug_string} {len(lines)} entries to {file_path}.")

        return file_path.stat()     # ---> return file stat info

    except Exception as e:
        raise IOServiceError(f"Failed to append file content: {file_path}.") from e



def write_or_append_lines_to_unique_file(file_path: Path, output_mode: str, lines: list[str]) -> os.stat_result:
    new_file_path = None
    current_file_content = None

    # preconditions
    match output_mode:
        case "x": #exclusive, not overwrite
            if file_path.exists(): raise IOServiceError(f"File already exists: {file_path.name}.")
        case "a":
            #check if output file has content, then load content
            if file_path.exists():
                current_file_content = file_path.read_text()
                # and put the content at the beginning of lines - array
                if (current_file_content):
                    lines.insert(0, current_file_content)


    temp_path = file_path.with_suffix(f".tmp_{os.getpid()}")

    try:
        with temp_path.open(mode="xt", encoding="utf-8") as f:
            for line in lines:
                f.write(f"{line.strip()}\n")

            # paranoid
            f.flush()
            os.fsync(f.fileno())

        # atomic swap
        os.replace(temp_path, file_path)
        logger.debug(f"{len(lines)} entries written to {file_path}.")

        return file_path.stat()     # ---> return file stat info

    except Exception as e:
        raise IOServiceError(f"Failed to write file content: {file_path}.") from e


import sys


class StdinReadError(Exception):
    """Raised when reading from standard input fails."""
    pass


def read_stdin_content(max_size_bytes: int = 10 * 1024 * 1024, encoding: str = "utf-8") -> str:
    """
    Reads all data from stdin and returns it as a string.

    Args:
        max_size_bytes: Memory limit to prevent DoS (default 10MB).
        encoding: The character encoding to use.

    Returns:
        The full content of stdin.

    Raises:
        StdinReadError: If decoding fails, size limit is exceeded, or I/O error occurs.
    """
    try:

        # If it is a terminal and not a pipe/file, we might want to skip reading
        if sys.stdin.isatty():
            return None

        # Read up to max_size + 1 to detect if input exceeds limit
        content = sys.stdin.read(max_size_bytes + 1)

        if len(content) > max_size_bytes:
            raise StdinReadError(f"Input size exceeds limit of {max_size_bytes} bytes")

        return content

    except UnicodeDecodeError as e:
        raise IOServiceError(f"Encoding error: Input is not valid {encoding}") from e
    except IOError as e:
        raise IOServiceError(f"I/O error during stdin read: {e}") from e
    except Exception as e:
        raise IOServiceError(f"Unexpected error while reading stdin: {e}") from e




class IOServiceError(Exception):
    pass