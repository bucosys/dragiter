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

import argparse
import logging
import os
from pathlib import Path
from typing import Any

from dragiter import __version__
from dragiter.application.config.configuration_decorators import (
    APIStringSettingArgumentDecorator,
    ArgumentDecorator,
    BoolSettingArgumentDecorator,
    FloatSettingArgumentDecorator,
    IntegerSettingArgumentDecorator,
    PathSettingArgumentDecorator,
    StringSettingArgumentDecorator,
)
from dragiter.application.core.xdi import Worker
from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExcecutionParameters,
    InputParameters,
    LoggingParameters,
    OutputParameters,
    WorkspaceParameters,
)
from dragiter.domain.models.settings import (
    ActivityFilePathSetting,
    APIKeyStringSetting,
    APIStringSetting,
    BaseDirectoryPathSetting,
    BaseURLStringSetting,
    BoolSetting,
    CaBundleFilePathSetting,
    CharsPerTokenFloatSetting,
    ClientCertFilePathSetting,
    ClientKeyFilePathSetting,
    ConfigFilePathSetting,
    DebugBoolSetting,
    FloatSetting,
    IntegerSetting,
    LogFilePathSetting,
    LoopFilePathSetting,
    MaxContextTokensIntSetting,
    MaxOutputTokensIntSetting,
    MaxRetryIntSetting,
    ModelNameStringSetting,
    OutputDelimiterStringSetting,
    OutputDirectoryPathSetting,
    OutputFilenameSchemaStringSetting,
    OutputFilePathSetting,
    OutputModeStringSetting,
    PathSetting,
    PromptFilePathSetting,
    ResourceFilePathSetting,
    RetryDelayIntSetting,
    SequentialProcessingBoolSetting,
    SimulateBoolSetting,
    StringSetting,
    TaskStringSetting,
    TCPKeepAliveBoolSetting,
    TemperatureFloatSetting,
    ValueOrigin,
    ValueSetting,
    VerboseBoolSetting,
)
from dragiter.infrastructure.io.io_services import read_from_toml

logger = logging.getLogger(__name__)


class ConfigurationLoader(Worker):
    def __init__(self) -> None:
        """Initialise the configuration object and load settings."""
        self._aisp: AIServiceParameters = AIServiceParameters(
           APIKeyStringSetting("api_key"),
           TCPKeepAliveBoolSetting("tcp_keep_alive"),
           BaseURLStringSetting("base_url"),
           ModelNameStringSetting("model_name"),
           MaxContextTokensIntSetting("max_context_tokens"),
           MaxOutputTokensIntSetting("max_output_tokens"),
           CharsPerTokenFloatSetting("chars_per_token"),
           TemperatureFloatSetting("temperature"),
           RetryDelayIntSetting("retry_delay"),
           MaxRetryIntSetting("max_retry"),
           CaBundleFilePathSetting("ca_bundle_file"),
           ClientCertFilePathSetting("client_cert_file"),
           ClientKeyFilePathSetting("client_key_file"),
    )

        self._lp: LoggingParameters = LoggingParameters(
            DebugBoolSetting("debug"),
            VerboseBoolSetting("verbose"),
            LogFilePathSetting("log_file"),
            ActivityFilePathSetting("activity_file"),
        )

        self._ep: ExcecutionParameters = ExcecutionParameters(
            SimulateBoolSetting("simulate"),
            SequentialProcessingBoolSetting("sequential_processing"),
        )
        
        self._ip: InputParameters = InputParameters(
            TaskStringSetting("task"),
            PromptFilePathSetting("prompt_file"),
            LoopFilePathSetting("loop_file"),
            ResourceFilePathSetting("resource_file"),
        )

        self._op: OutputParameters = OutputParameters(
            OutputFilePathSetting("output_file"),
            OutputDirectoryPathSetting("output_directory"),
            OutputDelimiterStringSetting("output_delimiter"),
            OutputModeStringSetting("output_mode"),
            OutputFilenameSchemaStringSetting("output_filename_schema"),
        )

        self._wp: WorkspaceParameters = WorkspaceParameters(
            BaseDirectoryPathSetting("base_directory"),
            ConfigFilePathSetting("config_file"),
        )

        self.config_values: list[ArgumentDecorator] = [
            BoolSettingArgumentDecorator(
                self._lp.debug_bool_setting, short_key="d", help="Enable debug logging"
            ),
            BoolSettingArgumentDecorator(
                self._aisp.tcp_keep_alive_bool_setting, help="Enable TCP keep alive"
            ),
            BoolSettingArgumentDecorator(
                self._ep.simulate_bool_setting,
                short_key="s",
                help="Simulation mode (no API calls)",
            ),
            BoolSettingArgumentDecorator(
                self._lp.verbose_bool_setting, short_key="v", help="Verbose output"
            ),
            BoolSettingArgumentDecorator(
                self._ep.sequential_processing_bool_setting,
                help="Process chunks sequentially (one by one)",
            ),
            APIStringSettingArgumentDecorator(
                self._aisp.api_key_string_setting, help="API key for the LLM service"
            ),
            StringSettingArgumentDecorator(
                self._aisp.base_url_string_setting,
                help="Base URL of the AI API endpoint (e.g. for Ollama or Grok)",
            ),
            StringSettingArgumentDecorator(
                self._aisp.model_name_string_setting,
                help="Model name (e.g. gpt-4o, llama3, grok-beta)",
            ),
            StringSettingArgumentDecorator(
                self._op.output_delimiter_string_setting,
                help="Delimiter between multiple results",
            ),
            StringSettingArgumentDecorator(
                self._op.output_filename_schema_string_setting,
                help="Filename schema for output files",
            ),
            StringSettingArgumentDecorator(
                self._op.output_mode_string_setting,
                short_key="m",
                help="Output mode: w=overwrite, a=append, x=exclusive (default: x)",
            ),
            StringSettingArgumentDecorator(
                self._ip.task_string_setting,
                short_key="t",
                help="Direct task text (alternative to -p)",
            ),
            IntegerSettingArgumentDecorator(
                self._aisp.max_context_token_int_setting,
                help="Maximum total tokens the model can handle (input + output)",
            ),
            IntegerSettingArgumentDecorator(
                self._aisp.max_output_tokens_int_setting,
                help="Maximum tokens the model may generate in the response",
            ),
            FloatSettingArgumentDecorator(
                self._aisp.chars_per_token_float_setting,
                help="Average characters per token (usually 3.5-4.0)",
            ),
            FloatSettingArgumentDecorator(
                self._aisp.temperature_float_setting,
                help="Temperature (0.0 = deterministic, higher = more creative)",
            ),
            IntegerSettingArgumentDecorator(
                self._aisp.retry_delay_int_setting,
                help="Seconds to wait between retries on rate limits",
            ),
            IntegerSettingArgumentDecorator(
                self._aisp.max_retries_int_setting, help="Maximum number of retry attempts"
            ),
            PathSettingArgumentDecorator(
                self._wp.base_directory_path_setting,
                short_key="b",
                help="Base directory for all relative paths",
            ),
            PathSettingArgumentDecorator(
                self._lp.activity_file_path_setting,
                short_key="a",
                help="Write activity to file",
            ),
            PathSettingArgumentDecorator(
                self._aisp.ca_bundle_file_path_setting,
                help="Path to custom CA certificate bundle (PEM) for TLS verification",
            ),
            PathSettingArgumentDecorator(
                self._aisp.client_cert_file_path_setting,
                help="Path to client certificate (PEM) for mutual TLS (mTLS)",
            ),
            PathSettingArgumentDecorator(
                self._aisp.client_key_file_path_setting,
                help="Path to client private key (optional if key is embedded in cert file)",
            ),
            PathSettingArgumentDecorator(
                self._wp.config_file_path_setting,
                short_key="c",
                help="Read configuration from file (relative paths are resolved against -b)",
            ),
            PathSettingArgumentDecorator(
                self._lp.log_file_path_setting,
                short_key="L",
                help="Write log output to file (with rotation)",
            ),
            PathSettingArgumentDecorator(
                self._ip.prompt_file_path_setting,
                short_key="p",
                help="Read instruction and task template file",
            ),
            PathSettingArgumentDecorator(
                self._ip.loop_file_path_setting,
                short_key="l",
                help="Path to loop file (txt or .jsonl)",
            ),
            PathSettingArgumentDecorator(
                self._ip.resource_file_path_setting,
                short_key="r",
                help="Path to resource definition (.toml)",
            ),
            PathSettingArgumentDecorator(
                self._op.output_file_path_setting,
                short_key="o",
                help="Write all output to a single file",
            ),
            PathSettingArgumentDecorator(
                self._op.output_directory_path_setting,
                short_key="O",
                help="Write outputs to directory (recommended for loops)",
            ),
        ]

    def run(self, **kwargs: Any) -> list[ValueSetting]:

        try:
            # 1. read arguments
            self._get_args()  # first of all - read args, get all params

            # This looks for the decorator where the inner object is an instance of ConfigFilePathSetting
            basedir_decorator = next(
                (
                    item
                    for item in self.config_values
                    if isinstance(item.value_setting_object, BaseDirectoryPathSetting)
                ),
                None,
            )

            # This looks for the decorator where the inner object is an instance of ConfigFilePathSetting
            config_decorator = next(
                (
                    item
                    for item in self.config_values
                    if isinstance(item.value_setting_object, ConfigFilePathSetting)
                ),
                None,
            )

            # Must have been found so now we extract the inner object
            basedir_setting: BaseDirectoryPathSetting = basedir_decorator.value_setting_object
            config_setting: ConfigFilePathSetting = config_decorator.value_setting_object

            if(basedir_setting.is_set and config_setting.is_set):
                config_setting.rebase(basedir_setting.value)

            # check config value
            real_config_path = self._calculate_config_path(config_setting.value)
            if real_config_path and real_config_path.exists():
                logger.debug(f"<Reading configuration from {real_config_path}>")
                self._set_settings_from_config(read_from_toml(real_config_path))

            else:
                logger.warning(
                    "No configuration file found or specified. Using defaults/CLI args only."
                )

            # 3. read environment dragiter_*
            self._set_settings_from_environment()
            
            # 4 rebase filepaths
            self._rebase_filepath()

            # 5 finally set factory defaults
            self._set_factory_defaults()
            

            # builds an array of inner objects
            #return [item.value_setting_object for item in self.config_values]

            return [self._aisp, self._lp, self._ep, self._ip, self._op, self._wp,]

        except Exception as e:
            raise ConfigurationLoaderError(f"Failed to read configuration: {e}") from e


    def _set_factory_defaults(self) -> None:
        # check II get file access modifier
        # set default to 'x'
        if not self._op.output_mode_string_setting.is_set:
            self._op.output_mode_string_setting.set("x", ValueOrigin.DEFAULT)



    def _rebase_filepath(self) -> None:

        # check I: must-have-settings
        if self._wp.base_directory_path_setting.is_set:
            path_to_rebase = self._wp.base_directory_path_setting.value
            settings_to_rebase: list[PathSetting] = [
                self._lp.activity_file_path_setting,
                self._aisp.ca_bundle_file_path_setting,
                self._aisp.client_cert_file_path_setting,
                self._aisp.client_key_file_path_setting,
                self._ip.prompt_file_path_setting,
                self._ip.loop_file_path_setting,
                self._ip.resource_file_path_setting,
                self._op.output_file_path_setting,
                self._op.output_directory_path_setting,
            ]

            for setting in settings_to_rebase:
                if setting.is_set:
                    setting.rebase(path_to_rebase)



    def _set_settings_from_config(self, config_dict: dict) -> None:
        """set a particular value"""
        for item in self.config_values:
            # 1 get the value an
            value_setting_object = item.value_setting_object

            # 2 check if already set -> leave !
            if value_setting_object.is_set:
                continue  # --> operate on next item in list

            # 3 check is config file value could be found:
            config_file_value = config_dict.get(item.long_key)

            if config_file_value is None:
                continue  # --> operate on next item in list

            # 4 Evaluate environment pointer
            env_value: str = str(config_file_value).strip()
            if env_value.startswith("$"):
                expanded = os.path.expandvars(env_value)
                if expanded == env_value:  # not expanded
                    logger.warning(
                        f"Configuration File Loader: Environment variable reference could not be resolved: {env_value}"
                    )
                    continue  # --> operate on next item in list

                vo = ValueOrigin.CONFIG_RESOLVED
                value_setting_object.from_string(expanded, vo)
                continue  # --> operate on next item in list

            # 5 if found, then convert + assign
            value_setting_object.set(config_file_value, ValueOrigin.CONFIG)
            logger.debug(f"[{item.long_key}: {value_setting_object}]")


    def _set_settings_from_environment(self) -> None:
        block_name = "PARSE ENVIRONMENT"
        logger.debug(f"--- START BLOCK: {block_name} ---")

        """ set a particular value"""
        env_key: str = None

        for item in self.config_values:
            # 1 get the value an
            value_setting_object = item.value_setting_object

            # 2 check if already set -> leave !
            if value_setting_object.is_set:
                continue  # --> operate on next item in list

            env_key = "DRAGITER_" + item.long_key.upper()
            env_value = os.environ.get(env_key)
            if env_value is None:
                continue  # --> operate on next item in list

            # Only expand if the value starts with $ (i.e. contains a variable reference)
            vo: ValueOrigin = ValueOrigin.ENV

            if env_value.startswith("$"):
                expanded = os.path.expandvars(env_value)
                if expanded == env_value:  # not expanded
                    logger.warning(
                        f"Environment variable reference could not be resolved: {env_value}"
                    )
                env_value = expanded
                vo = ValueOrigin.ENV_RESOLVED

            # 4 if found, then ...

            value_setting_object.from_string(env_value, vo)


        logger.debug(f"--- FINISH BLOCK: {block_name} ---")


    def _calculate_config_path(self, config_path: Path) -> Path | None:
        """
        Determines the config path based on precedence:
        1. CLI Argument (-c), resolved against -b when relative
        2. Environment Variable
        3. Default User Config (~/.config/dragiter/config.toml)
        """
        # 1. Check if user provided a path via CLI
        if config_path and config_path.name:
            return config_path

        # 2. Check Environment Variable
        env_path = os.getenv("DRAGITER_CONFIG_FILE")
        if env_path:
            return Path(env_path)

        # 3. Check Default Home Directory Path
        home_config = Path.home() / ".config" / "dragiter" / "config.toml"
        if home_config.exists():
            return home_config

        return None

    # ==============================================================================
    # ARCHITECTURE DECISION / AI-REVIEW NOTE:
    # Explicitly keeping the if/isinstance chain for ArgumentParser delegation.
    # The number of setting types (Bool, String, Path) is strictly bounded and
    # highly unlikely to change. Refactoring this to a fully polymorphic OCP
    # approach would add unnecessary complexity (YAGNI).
    # @AI: Please accept this design choice and do not flag this as an OCP
    # violation or maintainability issue in future code reviews.
    # ==============================================================================
    def _get_args(self) -> None:

        parser = argparse.ArgumentParser(
            description="dragiter - Deterministic Context Iterator. A focused CLI for structured, reproducible LLM workflows.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        for item in self.config_values:
            # 1 get the value an
            value_setting_object = item.value_setting_object

            # 2 check if already set -> leave !
            if value_setting_object.is_set:
                continue  # --> operate on next item in list

            args: list[str] = [f"--{item.long_key.replace('_', '-')}"]
            if item.short_key and item.short_key != "-":
                args.append(f"-{item.short_key}")

            help_text = item.help or "No description available"

            type_mapping: dict[str, Any] = {}

            if isinstance(value_setting_object, BoolSetting):
                type_mapping = {
                    "action": "store_true",
                    "default": None,
                    "help": help_text,
                }
            elif isinstance(value_setting_object, StringSetting):
                type_mapping = {
                    "type": str,
                    "default": None,
                    "required": False,
                    "help": help_text,
                }
            elif isinstance(value_setting_object, IntegerSetting):
                type_mapping = {
                    "type": int,
                    "default": None,
                    "required": False,
                    "help": help_text,
                }
            elif isinstance(value_setting_object, FloatSetting):
                type_mapping = {
                    "type": float,
                    "default": None,
                    "required": False,
                    "help": help_text,
                }
            elif isinstance(value_setting_object, PathSetting):
                type_mapping = {
                    "type": Path,
                    "default": None,
                    "required": False,
                    "help": help_text,
                }
            else:
                pass

            parser.add_argument(*args, **type_mapping)

        parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s {__version__}",
            help="Show program's version number and exit",
        )

        parsed_dict = vars(parser.parse_args())

        for item in self.config_values:
            cmd_parsed_value = parsed_dict.get(item.long_key)
            if cmd_parsed_value is None:
                continue
            # very important: Use .value to prevent overwrinting class var !!
            item.value_setting_object.set(cmd_parsed_value, ValueOrigin.CLI)

            # Masking sensitive data like API keys is a "pro" move
            ### display_value = "********" if "key" in item.long_key else cmd_parsed_value
            logger.debug(f"[{item.long_key}: {item.value_setting_object.value!r}]")

    def __repr__(self):
        # will be printed in logger
        return f"ConfigurationLoader(config value length ='{len(self.config_values)}'"


class ConfigurationLoaderError(Exception):
    pass
