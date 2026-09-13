# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import logging

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.chat_sessions import ChatSessions
from dragiter.domain.models.context_validation_report import ContextValidationReport
from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExecutionParameters,
    LoggingParameters,
)
from dragiter.domain.ports.payload_estimator import PayloadEstimator

logger = logging.getLogger(__name__)


class ContextWindowEstimator(Worker):

    def __init__(self, payload_estimator: PayloadEstimator) -> None:
        self._payload_estimator = payload_estimator

    def run(
        self,
        chat_sessions: ChatSessions,
        aisp: AIServiceParameters,
        lp: LoggingParameters,
        ep: ExecutionParameters,
    ) -> ContextValidationReport:

        if not (
            aisp.chars_per_token_float_setting.is_set
            and aisp.max_context_token_int_setting.is_set
            and aisp.max_output_tokens_int_setting.is_set
        ):
            logger.debug(
                "Neither chars-per-token nor max-context-tokens nor "
                "max-output-tokens are set. Validation is not applicable."
            )
            return ContextValidationReport(
                is_valid=None,
                total_tokens=0,
                max_tokens_limit=None,
                max_session_tokens=None,
            )

        if lp.verbose_bool_setting.value:
            logger.info(
                "Payload estimation: "
                f"chars-per-token: {aisp.chars_per_token_float_setting.value}, "
                f"max-context-tokens: {aisp.max_context_token_int_setting.value}, "
                f"max-output-tokens: {aisp.max_output_tokens_int_setting.value}"
            )

        out_tokens: int = aisp.max_output_tokens_int_setting.value
        limit: int = aisp.max_context_token_int_setting.value

        report = ContextValidationReport(
            is_valid=True,
            total_tokens=0,
            max_tokens_limit=limit,
            chars_per_token=aisp.chars_per_token_float_setting.value,
            max_output_tokens=out_tokens,
        )

        try:

            calc_input_tokens: int = 0

            for index, chat_session in enumerate(chat_sessions.session_list):
                calc_input_tokens = self._payload_estimator.estimate(
                    chat_session.input_chat_message_list,
                    aisp.chars_per_token_float_setting.value)

                tot_tokens: int = calc_input_tokens + out_tokens

                report.total_tokens += tot_tokens
                report.session_token_counts[index] = tot_tokens
                report.session_input_token_counts[index] = calc_input_tokens

                # Track the maximal value (High-Water Mark)
                if (
                    report.max_session_tokens is None
                    or tot_tokens > report.max_session_tokens
                ):
                    report.max_session_tokens = tot_tokens
                    report.max_session_index = index

                if lp.verbose_bool_setting.value:
                    logger.info(
                        f"Calculated input token amount: {calc_input_tokens} | "
                        f"Output reservation: {out_tokens} | "
                        f"Calculated total: {tot_tokens} | "
                        f"Limit: {limit}"
                    )

                if (calc_input_tokens + out_tokens) > aisp.max_context_token_int_setting.value:
                    logger.warning(
                        f"Context window exceeded. "
                        f"Input: {calc_input_tokens} | Output reservation: {out_tokens} | "
                        f"Calculated total: {calc_input_tokens + out_tokens} | "
                        f"Limit: {aisp.max_context_token_int_setting.value}"
                    )

                    failed_message = (
                        f"The estimated input tokens ({calc_input_tokens}) plus the reserved output tokens ({out_tokens}) "
                        f"exceed the total context window limit ({aisp.max_context_token_int_setting.value})."
                    )

                    report.is_valid = False
                    report.simulation_warnings.append(failed_message)
                    if not ep.simulate_bool_setting.value:
                        raise ContextWindowValidatorError(
                            f"Validation failed at messages block index {index}: {failed_message}"
                        )

            if lp.verbose_bool_setting.value:
                logger.info(
                    f"Context estimation summary: "
                    f"total_tokens={report.total_tokens}, "
                    f"max_session_tokens={report.max_session_tokens} "
                    f"(session {report.max_session_index}), "
                    f"is_valid={report.is_valid}"
                )

            return report

        except ContextWindowValidatorError:
            raise
        except Exception as e:
            raise ContextWindowValidatorError(
                f"Failed to validate context window due to that reason: {e}"
            ) from e


class ContextWindowValidatorError(Exception):
    pass
