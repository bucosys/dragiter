from multiprocessing.util import debug

from dragiter.domain.models.chat_sessions import ChatSessions, ChatSession
from dragiter.domain.models.settings import CharsPerTokenFloatSetting, MaxInputTokensIntSetting, MaxOutputTokensIntSetting, SimulateBoolSetting, \
    VerboseBoolSetting
from dragiter.application.core.xdi import *

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


        if not (chars_per_token_float_setting.is_set and max_input_tokens_int_setting.is_set and max_output_tokens_int_setting.is_set):
            logger.debug(f"Neither chars-per-token nor max-input-tokens-int-setting nor max-output-tokens-int-setting are set. Validation is not applicable.")
            return None


        if verbose_boolean_setting.value:
            # show current settings
            logger.debug(f"Payload estimation: "
                         f"chars-per-token: {chars_per_token_float_setting.value}, "
                         f"max-input-tokens: {max_input_tokens_int_setting.value}, "
                         f"max-output-tokens: {max_output_tokens_int_setting.value}")

        try:

            calc_input_token_amount: int = 0
            counter: int = 0
            for chat_session in chat_sessions.session_list:
                calc_input_token_amount = self._payload_estimator.estimate(
                    chat_session.input_chat_message_list,
                    chars_per_token_float_setting.value)


                if verbose_boolean_setting.value:
                    debug(f"Calculated input token amount: {calc_input_token_amount}")

                if calc_input_token_amount > max_input_tokens_int_setting.value:
                    debug(f"Simulated input token amount: {calc_input_token_amount} is larger than max-input-tokens-int-setting value.")
                    if not simulation_boolean_setting.value:
                        # real life
                        raise ContextWindowValidatorError(f"Validation failed at messages block index {counter}: ")

                counter += 1


        except Exception as e:
            raise ContextWindowValidatorError(f"Failed to validate context window due to that reason: {e}") from e

        finally:
            return None



class ContextWindowValidatorError(Exception):
    pass