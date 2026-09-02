# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import logging

from dragiter.domain.models.chat_sessions import ChatMessage
from dragiter.domain.ports.payload_estimator import PayloadEstimator, PayloadEstimatorError

logger = logging.getLogger(__name__)


class SimplePayloadEstimator(PayloadEstimator):
    def estimate(self, chat_messages: list[ChatMessage], chars_per_token: float) -> int:

        if len(chat_messages) < 1:
            raise SimplePayloadEstimatorError('Empty chat messages')

        if chars_per_token < 0.1:
            raise SimplePayloadEstimatorError('chars per token cannot be less than 0.1')

        total_chars = sum(
            len(msg.content) for msg in chat_messages if msg.content
        )

        estimated_tokens = int(total_chars / chars_per_token)
        logger.debug(f"Payload estimation: {total_chars} chars -> ~{estimated_tokens} tokens.")

        return estimated_tokens


class SimplePayloadEstimatorError(PayloadEstimatorError):
    pass


