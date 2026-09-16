# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import json
import logging
import os
from pathlib import Path
import sys
import tomllib

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


def write_lines_to_unique_file(
    file_path: Path, overwrite: bool, lines: list[str]
) -> os.stat_result:
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

        return file_path.stat()  # ---> return file stat info

    except Exception as e:
        raise IOServiceError(f"Failed to write file content: {file_path}.") from e


def append_jsonl_to_file(file_path: Path, lines: list[dict]) -> os.stat_result:
    debug_string = "Appended" if file_path.exists() else "Write"

    try:
        with file_path.open(mode="a", encoding="utf-8") as f:
            for line in lines:
                jsonl = json.dumps(line, ensure_ascii=False, default=str)
                # JSONL safety: json.dumps(ensure_ascii=False) does not escape
                # U+0085 (NEL), U+2028 (LINE SEPARATOR) and U+2029 (PARAGRAPH SEPARATOR).
                # These characters act as line breaks and would break the one-object-per-line
                # guarantee of JSONL. We escape them explicitly while keeping all other
                # Unicode characters readable.
                jsonl = (
                    jsonl.replace("\u0085", "\\u0085")
                    .replace("\u2028", "\\u2028")
                    .replace("\u2029", "\\u2029")
                )

                f.write(jsonl + "\n")

            # paranoid
            f.flush()
            os.fsync(f.fileno())

        logger.debug(f"{debug_string} {len(lines)} entries to {file_path}.")

        return file_path.stat()  # ---> return file stat info

    except Exception as e:
        raise IOServiceError(f"Failed to append file content: {file_path}.") from e


def write_or_append_lines_to_unique_file(
    file_path: Path, output_mode: str, lines: list[str]
) -> os.stat_result:

    try:
        if output_mode == "a":
            with file_path.open(mode="at", encoding="utf-8") as f:
                for line in lines:
                    f.write(f"{line.strip()}\n")

                # paranoid
                f.flush()
                os.fsync(f.fileno())

            logger.debug(f"{len(lines)} entries appended to {file_path}.")
            return file_path.stat()

        else:
            if output_mode == "x" and file_path.exists():
                raise IOServiceError(f"File already exists: {file_path.name}.")

            temp_path = file_path.with_suffix(f".tmp_{os.getpid()}")

            with temp_path.open(mode="xt", encoding="utf-8") as f:
                for line in lines:
                    f.write(f"{line.strip()}\n")

                # paranoid
                f.flush()
                os.fsync(f.fileno())

            # atomic swap
            os.replace(temp_path, file_path)
            logger.debug(f"{len(lines)} entries written to {file_path}.")

            return file_path.stat()  # ---> return file stat info

    except Exception as e:
        raise IOServiceError(f"Failed to write file content: {file_path}.") from e


class StdinReadError(Exception):
    """Raised when reading from standard input fails."""

    pass


def read_stdin_content(
    max_size_bytes: int = 10 * 1024 * 1024, encoding: str = "utf-8"
) -> str | None:
    """
    Read all data from stdin and return it as a string.

    Callers must invoke this only when stdin is part of the contract
    (``{STDIN}`` in the prompt template, or ``-t`` / ``--task``). A
    blocking ``read()`` on a non-TTY that never reaches EOF hangs the
    process (CI, systemd, Docker without ``-i``).

    Args:
        max_size_bytes: Memory limit to prevent DoS (default 10MB).
        encoding: The character encoding to use.

    Returns:
        The full content of stdin, or ``None`` when stdin is a TTY.

    Raises:
        IOServiceError: If decoding fails, the size limit is exceeded, or an I/O error occurs.
        StdinReadError: If the configured size limit is exceeded.
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
    except OSError as e:
        raise IOServiceError(f"I/O error during stdin read: {e}") from e
    except Exception as e:
        raise IOServiceError(f"Unexpected error while reading stdin: {e}") from e


class IOServiceError(Exception):
    pass
