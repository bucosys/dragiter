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


class LoggingConfigurator:

    @staticmethod
    def parse_and_configure() -> LoggingConfiguration:

        app_name = sys.argv[0]
        env_debug_variable = app_name.upper() + "_DEBUG"
        env_verbose_variable = app_name.upper() + "_VERBOSE"


        argv_lower = [a.lower() for a in sys.argv]

        debug = (
            "--debug" in argv_lower or "-d" in argv_lower or
            os.environ.get(env_debug_variable, "").upper() in ("TRUE", "1", "YES")
        )

        verbose = (
            "--verbose" in argv_lower or "-v" in argv_lower or
            os.environ.get(env_verbose_variable, "").upper() in ("TRUE", "1", "YES")
        )


        log_level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)

        # Logging config
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            stream=sys.stderr,
            force=True
        )

        logger = logging.getLogger(__name__)
        logger.info(f"Logging initialized (level={logging.getLevelName(log_level)})")

        if debug:
            logger.debug(f"Debug mode enabled | CWD: {Path.cwd()}")
        if verbose and not debug:
            logger.info("Verbose mode enabled")

        return LoggingConfiguration(debug=debug, verbose=verbose, log_level=log_level)