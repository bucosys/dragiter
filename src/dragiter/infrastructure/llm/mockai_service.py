# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from datetime import datetime
import logging

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import AIServiceParameters, LoggingParameters
from dragiter.domain.ports.llm_service import LLMService, LLMServiceError
from dragiter.domain.ports.stream_progress_listener import StreamProgressListener

logger = logging.getLogger(__name__)


class MockAIServiceError(LLMServiceError):
    pass


class MockAIService(LLMService):
    """
    Stands in for a real LLM in simulate mode.

    Its own reply content is never user-facing: ChatManager overwrites it with the
    session's board and complete outgoing request before persisting (SIMU).
    """

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
            chat_result = ChatResult()
            chat_result.started_at = datetime.now()
            chat_result.output_chat_message.content = ""
            chat_result.finish_reason = "mock"
            chat_result.ended_at = datetime.now()
            chat_result.duration_ms = int((chat_result.ended_at - chat_result.started_at).total_seconds() * 1000)

            return chat_result

        except Exception as e:
            raise MockAIServiceError(f"MockAIService failed: {e}") from e

