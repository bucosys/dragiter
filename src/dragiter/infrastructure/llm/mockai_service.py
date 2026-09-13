# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from datetime import datetime
import json
import logging

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import AIServiceParameters, LoggingParameters
from dragiter.domain.ports.llm_service import LLMService, LLMServiceError
from dragiter.domain.ports.payload_estimator import PayloadEstimator
from dragiter.domain.ports.stream_progress_listener import StreamProgressListener

logger = logging.getLogger(__name__)


class MockAIServiceError(LLMServiceError):
    pass


class MockAIService(LLMService):

    def __init__(self, payload_estimator: PayloadEstimator = None):
        self.payload_estimator = payload_estimator

    def process_query(
        self,
        aisp: AIServiceParameters,
        lp: LoggingParameters,
        chat_session: ChatSession,
        progress: StreamProgressListener | None = None,
    ) -> ChatResult:
        if not chat_session or not chat_session.input_chat_message_list:
            raise MockAIServiceError("ChatSession or input messages are empty")
        _ = progress

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

