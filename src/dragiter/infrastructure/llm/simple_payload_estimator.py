import logging

from dragiter.domain.models.chat_sessions import ChatMessage
from dragiter.domain.ports.payload_estimator import PayloadEstimator, PayloadEstimatorError

logger = logging.getLogger(__name__)


class SimplePayloadEstimator(PayloadEstimator):
    def estimate(self, chat_messages: list[ChatMessage], chars_per_token: float) -> int:

        if len(chat_messages) < 1:
            raise SimplePayloadEstimatorError(f'Empty chat messages')

        if chars_per_token < 0.1:
            raise SimplePayloadEstimatorError(f'chars per token cannot be less than 0.1')

        total_chars = sum(
            len(msg.content) for msg in chat_messages if msg.content
        )

        estimated_tokens = int(total_chars / chars_per_token)
        logger.debug(f"Payload estimation: {total_chars} chars -> ~{estimated_tokens} tokens.")

        return estimated_tokens


class SimplePayloadEstimatorError(PayloadEstimatorError):
    pass

    #     # check limits if demanded:
    #     if max_token_setting.is_set:
    #         # 1. Calculate total character length of entire payload
    #         total_chars = sum(
    #             len(msg.get("content") or "") for msg in messages
    #         )
    #         # 2. Apply chars_per_token (user configurable, default 4.0)
    #         chars_per_token = chars_per_token_setting.value or 4.0
    #         estimated_tokens = int(
    #             total_chars / chars_per_token) + 150  # +150 for overhead (system, formatting, etc.)
    #
    #         if estimated_tokens >= max_token_setting.value:
    #             logstring = f"""
    # CRITICAL: Payload exceeds model context window!
    # Estimated tokens: {estimated_tokens:,} > {max_token_setting.value:,}
    # Recommendation: Reduce material, tighten regex filters, or use a larger model.
    #                         """
    #
    #             if simulation_boolean_setting:
    #                 logger.debug(logstring)
    #             else:
    #                 raise ChatManagerError(logstring)  # party is over in real mode !
    #
    #         else:
    #             logger.debug(f"Estimated tokens: {estimated_tokens:,}")
    #
