# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dataclasses import dataclass
import logging
import os

from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExcecutionParameters,
    InputParameters,
    LoggingParameters,
    OutputParameters,
    WorkspaceParameters,
)

logger = logging.getLogger(__name__)


# Configuration Validator Issue (CVI)
@dataclass
class ConfigurationValidatorFinding:
    rule: str
    finding: str
    description: str = None


class ConfigurationValidator:
    def __init__(self) -> None:
        """Modify and validate the configuration"""

    def run(
        self,
        aisp: AIServiceParameters,
        lp: LoggingParameters,
        ep: ExcecutionParameters,
        ip: InputParameters,
        op: OutputParameters,
        wp: WorkspaceParameters,
    ) -> None:


        try:
            CVF = ConfigurationValidatorFinding  # shorthand
            cvfs: list[CVF] = []

            if ip.task_string_setting.is_set:  # so if user choose that param
                if ip.task_string_setting.value.strip() == "":
                    cvfs.append(
                        CVF(
                            ip.task_string_setting.key,
                            "value not set",
                            "No task recognizable",
                        )
                    )

            else:  # there will no prompt file read in...
                if not ip.prompt_file_path_setting.is_set:
                    cvfs.append(
                        CVF(
                            ip.prompt_file_path_setting.key,
                            "value not set",
                            "Path to prompt file is mandatory.",
                        )
                    )
                else:
                    pfps_value = ip.prompt_file_path_setting.value
                    if not os.access(pfps_value, os.R_OK):
                        cvfs.append(
                            CVF(
                                ip.prompt_file_path_setting.key,
                                f"File not readable: {pfps_value}",
                                "Path to prompt file is mandatory. The given file is not readable.",
                            )
                        )

            if not ep.simulate_bool_setting.value and not aisp.base_url_string_setting.is_set:
                cvfs.append(
                    CVF(
                        aisp.base_url_string_setting.key,
                        "value not set",
                        "Path to LLM is mandatory.",
                    )
                )


            if op.output_mode_string_setting.value not in {"a", "x", "w"}:
                cvfs.append(
                    CVF(
                        op.output_mode_string_setting.key,
                        "If file open mode is set, use one of a (append), w (overwrite) or x (exclusive)",
                    )
                )

            # stage 1 check for reading a file or director
            input_path_settings_to_check = [
                wp.base_directory_path_setting,
                aisp.ca_bundle_file_path_setting,
                aisp.client_cert_file_path_setting,
                aisp.client_key_file_path_setting,
                ip.loop_file_path_setting,
                ip.resource_file_path_setting,
                op.output_directory_path_setting,
            ]

            cvfs.extend(
                [
                    CVF(setting.key, f"Path not readable: {setting.value}")
                    for setting in input_path_settings_to_check
                    if setting.is_set and not os.access(setting.value, os.R_OK)
                ]
            )

            # stage II check for wrinting a sinle file, check directory
            output_path_settings_to_check = [
                lp.activity_file_path_setting,
                lp.log_file_path_setting,
                op.output_file_path_setting,
            ]

            cvfs.extend(
                [
                    CVF(setting.key, f"Directory not readable: {setting.value.parent}")
                    for setting in output_path_settings_to_check
                    if setting.is_set and not os.access(setting.value.parent, os.R_OK)
                ]
            )

            # stage IIb: -o / -a existence against -m (output_mode)
            # x = exclusive create (file must not exist)
            # w = overwrite (existing file must be writable)
            # a = append     (existing file must be writable)
            output_mode = (
                op.output_mode_string_setting.value
                if op.output_mode_string_setting.is_set
                else "x"
            )
            mode_targets = [
                op.output_file_path_setting,
            ]
            if output_mode in {"a", "x", "w"}:
                for setting in mode_targets:
                    if not setting.is_set:
                        continue
                    target = setting.value
                    if output_mode == "x" and target.exists():
                        cvfs.append(
                            CVF(
                                setting.key,
                                f"File already exists: {target}",
                                "output_mode=x (exclusive) forbids an existing "
                                f"{setting.key}. Use -m w to overwrite or -m a to append.",
                            )
                        )
                    elif (
                        output_mode in {"a", "w"}
                        and target.exists()
                        and not os.access(target, os.W_OK)
                    ):
                        cvfs.append(
                            CVF(
                                setting.key,
                                f"File not writable: {target}",
                                f"output_mode={output_mode} requires write access to "
                                f"an existing {setting.key}.",
                            )
                        )

            # stage III: LLM settings
            if aisp.max_retries_int_setting.is_set and (
                    aisp.max_retries_int_setting.value < 0
                    or aisp.max_retries_int_setting.value > 9
                ):
                    cvfs.append(
                        CVF(
                            aisp.max_retries_int_setting.key,
                            f"value should be between 0 and 9 inclusive, not {aisp.max_retries_int_setting.value}",
                        )
                    )

            if aisp.retry_delay_int_setting.is_set and (
                    aisp.retry_delay_int_setting.value < 0
                    or aisp.retry_delay_int_setting.value > 20
                ):
                    cvfs.append(
                        CVF(
                            aisp.retry_delay_int_setting.key,
                            f"value should be between 0 and 20 inclusive, not {aisp.retry_delay_int_setting.value}",
                        )
                    )

            if aisp.chars_per_token_float_setting.is_set and aisp.chars_per_token_float_setting.value <= 0.0:
                    cvfs.append(
                        CVF(
                            aisp.chars_per_token_float_setting.key,
                            f"value should not be less than 0.0: {aisp.chars_per_token_float_setting.value}",
                        )
                    )

            # Stage IV Cert
            if (
                aisp.client_key_file_path_setting.is_set
                and not aisp.client_cert_file_path_setting.is_set
            ):
                cvfs.append(
                    CVF(
                        aisp.client_key_file_path_setting.key,
                        "client_key given without client_cert",
                        "A client private key requires a client certificate (--client-cert).",
                    )
                )


            if len(cvfs) > 0:
                raise ConfigurationValidatorError(cvfs)



            return None

        except ConfigurationValidatorError:
            raise  #
        except Exception as e:
            raise ConfigurationValidatorError(
                f"Unexpected exception occurred: {e}"
            ) from e


class ConfigurationValidatorError(Exception):
    pass
