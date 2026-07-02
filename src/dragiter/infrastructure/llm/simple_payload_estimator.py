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


