# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""Unit tests for MockAIService's empty-session guard."""

from __future__ import annotations

import pytest
from support import blank_parameter_groups

from dragiter.domain.models.chat_sessions import ChatMessage, ChatSession
from dragiter.infrastructure.llm.mockai_service import MockAIService, MockAIServiceError


def test_empty_session_raises_mock_ai_service_error() -> None:
    """Covers SIMU-06."""
    groups = blank_parameter_groups()
    session = ChatSession(input_chat_message_list=[])

    with pytest.raises(MockAIServiceError):
        MockAIService().process_query(groups["aisp"], groups["lp"], session)


def test_session_with_messages_does_not_raise() -> None:
    """Sanity check alongside SIMU-06: a real session is unaffected."""
    groups = blank_parameter_groups()
    session = ChatSession(
        input_chat_message_list=[ChatMessage(role="user", content="ask")]
    )

    result = MockAIService().process_query(groups["aisp"], groups["lp"], session)

    assert result.finish_reason == "mock"
    # MockAIService's own content is never user-facing: ChatManager overwrites it
    # with the session's board and complete request before persisting.
    assert result.output_chat_message.content == ""
