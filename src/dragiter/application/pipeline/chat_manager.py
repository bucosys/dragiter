# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import logging

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.chat_sessions import ChatSessions
from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExecutionParameters,
    LoggingParameters,
)
from dragiter.domain.ports.llm_service import LLMService
from dragiter.infrastructure.llm.mockai_service import MockAIService
from dragiter.infrastructure.llm.simple_payload_estimator import SimplePayloadEstimator

logger = logging.getLogger(__name__)


class ChatManager(Worker):
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    def run(self,
            aisp: AIServiceParameters,
            lp: LoggingParameters,
            ep: ExecutionParameters,
            chat_sessions: ChatSessions,
            ) -> ChatResults:

        chat_result_list: list[ChatResult] = []

        try:


            # use the mock service if simulation process requested
            if ep.simulate_bool_setting.value:
                payload_estimator = SimplePayloadEstimator()
                self.llm_service = MockAIService(payload_estimator)

            for session in chat_sessions.session_list:
                chat_result_list.append(self.llm_service.process_query(aisp, lp, session))

            return ChatResults(chat_result_list)

        except Exception as e:
            raise ChatManagerError(f"Failed to process openai query: {e}") from e


class ChatManagerError(Exception):
    pass
