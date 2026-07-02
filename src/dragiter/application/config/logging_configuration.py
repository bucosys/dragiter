# =============================================================================
# dragiter - Deterministic RAG Iterator
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

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoggingConfiguration:
    debug: bool
    verbose: bool
    log_level: int
    log_file: Path | None = None


class LoggingConfigurator:

    @staticmethod
    def parse_and_configure() -> LoggingConfiguration:

        app_name = sys.argv[0]
        env_debug_variable = app_name.upper() + "_DEBUG"
        env_verbose_variable = app_name.upper() + "_VERBOSE"
        env_log_file_variable = app_name.upper() + "_LOG_FILE"
        env_base_dir_variable = app_name.upper() + "_BASE_DIRECTORY"

        argv_lower = [a.lower() for a in sys.argv]

        debug = (
                "--debug" in argv_lower or "-d" in argv_lower or
                os.environ.get(env_debug_variable, "").upper() in ("TRUE", "1", "YES")
        )

        verbose = (
                "--verbose" in argv_lower or "-v" in argv_lower or
                os.environ.get(env_verbose_variable, "").upper() in ("TRUE", "1", "YES")
        )

        # === Parse command line arguments ===
        log_file_arg = None
        base_dir_arg = None

        for i, arg in enumerate(sys.argv):
            if arg in ("--log-file", "-L"):
                if i + 1 < len(sys.argv):
                    log_file_arg = sys.argv[i + 1]
            if arg in ("--base-directory", "-b"):
                if i + 1 < len(sys.argv):
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

        log_level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)

        # === Console logging (stderr) ===
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            stream=sys.stderr,
            force=True
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
        if verbose and not debug:
            logger.info("Verbose mode enabled")

        return LoggingConfiguration(
            debug=debug,
            verbose=verbose,
            log_level=log_level,
            log_file=log_file
        )