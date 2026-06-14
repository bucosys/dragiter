from multiprocessing.util import debug

from dragiter.application.core.xdi import *
from dragiter.domain.models.chat_sessions import ChatSessions
from dragiter.domain.models.context_validation_report import ContextValidationReport
from dragiter.domain.models.settings import CharsPerTokenFloatSetting, MaxInputTokensIntSetting, \
    MaxOutputTokensIntSetting, SimulateBoolSetting, \
    VerboseBoolSetting
from dragiter.domain.ports.payload_estimator import PayloadEstimator

logger = logging.getLogger(__name__)


class ContextWindowEstimator:

    def __init__(self, payload_estimator: PayloadEstimator) -> None:
        self._payload_estimator = payload_estimator

    def run(self,
            chat_sessions: ChatSessions,
            verbose_boolean_setting: VerboseBoolSetting,
            simulation_boolean_setting: SimulateBoolSetting,
            chars_per_token_float_setting: CharsPerTokenFloatSetting,
            max_input_tokens_int_setting: MaxInputTokensIntSetting,
            max_output_tokens_int_setting: MaxOutputTokensIntSetting
            ) -> None:

        if not (
                chars_per_token_float_setting.is_set and max_input_tokens_int_setting.is_set and max_output_tokens_int_setting.is_set):
            logger.debug(
                f"Neither chars-per-token nor max-input-tokens-int-setting nor max-output-tokens-int-setting are set. Validation is not applicable.")
            return None

        if verbose_boolean_setting.value:
            # show current settings
            logger.debug(f"Payload estimation: "
                         f"chars-per-token: {chars_per_token_float_setting.value}, "
                         f"max-input-tokens: {max_input_tokens_int_setting.value}, "
                         f"max-output-tokens: {max_output_tokens_int_setting.value}")

        out_tokens: int = max_output_tokens_int_setting.value
        limit: int = max_input_tokens_int_setting.value + out_tokens

        report = ContextValidationReport(
            is_valid=True,
            total_tokens=0,
            max_tokens_limit=limit
        )

        try:

            calc_input_tokens: int = 0

            for index, chat_session in enumerate(chat_sessions.session_list):
                calc_input_tokens = self._payload_estimator.estimate(
                    chat_session.input_chat_message_list,
                    chars_per_token_float_setting.value)

                tot_tokens: int = calc_input_tokens + out_tokens

                report.total_tokens += tot_tokens
                report.session_token_counts[index] = tot_tokens

                # Track the maximal value (High-Water Mark)
                if tot_tokens > report.max_session_tokens:
                    report.max_session_tokens = tot_tokens
                    report.max_session_index = index

                if verbose_boolean_setting.value:
                    debug(f"Calculated input token amount: {calc_input_tokens}")

                if calc_input_tokens > max_input_tokens_int_setting.value:
                    debug(
                        f"Simulated input token amount: {calc_input_tokens} is larger than max-input-tokens-int-setting value.")
                    failed_message = f"Token amount ({calc_input_tokens}) exceeds max limcalc_input_token_amountit ({max_input_tokens_int_setting.value})."
                    report.is_valid = False
                    report.simulation_warnings.append(failed_message)
                    if not simulation_boolean_setting.value:
                        # real life
                        raise ContextWindowValidatorError(f"Validation failed at messages block index {index}: ")

            return report

        except Exception as e:
            raise ContextWindowValidatorError(f"Failed to validate context window due to that reason: {e}") from e


class ContextWindowValidatorError(Exception):
    pass
