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
import logging

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.chat_results import ChatResult, ChatResults
from dragiter.domain.models.chat_sessions import ChatSessions
from dragiter.domain.models.parameters import (
    AIServiceParameters,
    ExcecutionParameters,
    LoggingParameters,
)
from dragiter.domain.models.settings import SimulateBoolSetting
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
            ep: ExcecutionParameters,
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
