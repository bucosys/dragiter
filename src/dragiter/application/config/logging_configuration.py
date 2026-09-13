# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import sys


@dataclass(frozen=True)
class LoggingConfiguration:
    debug: bool
    verbose: bool
    log_level: int
    log_file: Path | None = None


class LoggingConfigurator:

    @staticmethod
    def parse_and_configure() -> LoggingConfiguration:

        app_name = ""
        env_debug_variable = "DRAGITER_DEBUG"
        env_verbose_variable = "DRAGITER_VERBOSE"
        env_log_file_variable = "DRAGITER_LOG_FILE"
        env_base_dir_variable = "DRAGITER_BASE_DIRECTORY"

        argv_lower = [a.lower() for a in sys.argv]

        debug = (
                "--debug" in argv_lower or "-d" in argv_lower or
                os.environ.get(env_debug_variable, "").strip().upper() in ("TRUE", "1", "YES")
        )

        verbose = (
                "--verbose" in argv_lower or "-v" in argv_lower or
                os.environ.get(env_verbose_variable, "").strip().upper() in ("TRUE", "1", "YES")
        )

        # === Parse command line arguments ===
        log_file_arg = None
        base_dir_arg = None

        for i, arg in enumerate(sys.argv):
            if arg in ("--log-file", "-L") and (i + 1 < len(sys.argv)):
                log_file_arg = sys.argv[i + 1]
            if arg in ("--base-directory", "-b") and (i + 1 < len(sys.argv)):
                base_dir_arg = sys.argv[i + 1]

        # === Determine base directory (only needed for relative log file paths) ===
        if base_dir_arg:
            base_dir = Path(base_dir_arg).resolve()
        else:
            env_base = os.environ.get(env_base_dir_variable)
            if env_base:
                base_dir = Path(env_base).resolve()
            else:
                base_dir = Path.cwd()

        # === Determine log file (only if explicitly requested) ===
        log_file = None

        if log_file_arg:
            log_path = Path(log_file_arg)
            if log_path.is_absolute():
                log_file = log_path
            else:
                # Relative path → resolve against base directory
                log_file = (base_dir / log_path).resolve()
        else:
            # Only from environment variable (no automatic debug fallback)
            env_log = os.environ.get(env_log_file_variable)
            if env_log:
                log_file = Path(env_log)

        # ``-v`` drives the stderr board, not the root logger. Only ``-d``
        # raises the process log level.
        log_level = logging.DEBUG if debug else logging.WARNING

        # === Console logging (stderr) ===
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            stream=sys.stderr,
            force=True
        )

        for noisy in ("httpx2", "httpx", "httpcore", "openai"):
            logging.getLogger(noisy).setLevel(
                logging.NOTSET if debug else logging.WARNING
            )

        # === File logging (simple append, no rotation) ===
        if log_file:
            file_handler = logging.FileHandler(
                filename=str(log_file),
                mode='a',           # append mode
                encoding='utf-8',
                delay=True
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
            ))
            logging.getLogger().addHandler(file_handler)

        logger = logging.getLogger(__name__)
        logger.info(f"Logging initialized (level={logging.getLevelName(log_level)})")

        if log_file:
            logger.info(f"File logging enabled → {log_file}")

        if debug:
            logger.debug(f"Debug mode enabled | CWD: {Path.cwd()}")

        return LoggingConfiguration(
            debug=debug,
            verbose=verbose,
            log_level=log_level,
            log_file=log_file
        )
