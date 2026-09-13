# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from typing import Protocol, runtime_checkable

from dragiter.domain.models.chat_results import ChatResult
from dragiter.domain.models.chat_sessions import ChatSession
from dragiter.domain.models.parameters import AIServiceParameters, LoggingParameters
from dragiter.domain.ports.stream_progress_listener import StreamProgressListener


@runtime_checkable
class LLMService(Protocol):
    def process_query(
        self,
        aisp: AIServiceParameters,
        lp: LoggingParameters,
        chat_session: ChatSession,
        progress: StreamProgressListener | None = None,
    ) -> ChatResult: ...


class LLMServiceError(Exception):
    pass
