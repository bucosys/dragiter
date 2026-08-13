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

import json
import logging
from datetime import datetime

from dragiter.domain.models.ai_service_parameters import AIServiceParameters
from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.ports.llm_service import LLMService, LLMServiceError

from dragiter.domain.ports.payload_estimator import PayloadEstimator




logger = logging.getLogger(__name__)


class MockAIServiceError(LLMServiceError):
    pass


class MockAIService(LLMService):

    def __init__(self, payload_estimator: PayloadEstimator = None):
        self.payload_estimator = payload_estimator

    def process_query(self, aisp: AIServiceParameters, chat_session: ChatSession) -> ChatResult:
        if not chat_session or not chat_session.input_chat_message_list:
            raise MockAIServiceError("ChatSession or input messages are empty")

        try:
            last_msg = chat_session.input_chat_message_list[-1]

            # === Token Estimation ===
            estimated_tokens = None
            if self.payload_estimator and aisp.chars_per_token_float_setting.is_set:
                estimated_tokens = self.payload_estimator.estimate(
                    chat_session.input_chat_message_list,
                    aisp.chars_per_token_float_setting.value
                )

            # Build mock response
            mock_data = {
                "mock": True,
                "timestamp": datetime.now().isoformat(),
                "model": aisp.model_name_string_setting.value,
                "input_message_count": len(chat_session.input_chat_message_list),
                "estimated_input_tokens": estimated_tokens,
                "last_role": last_msg.role,
                "last_content_preview": (last_msg.content or "")[:300],
                "full_content": last_msg.content,
            }

            chat_result = ChatResult()
            chat_result.started_at = datetime.now()
            chat_result.output_chat_message.content = json.dumps(mock_data, ensure_ascii=False, indent=2)
            chat_result.finish_reason = "mock"
            chat_result.ended_at = datetime.now()
            chat_result.duration_ms = int((chat_result.ended_at - chat_result.started_at).total_seconds() * 1000)

            return chat_result

        except Exception as e:
            raise MockAIServiceError(f"MockAIService failed: {e}") from e

