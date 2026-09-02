# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold


from dragiter.domain.ports.llm_service import LLMService


class LLMServiceAdapter(LLMService):
    def __init__(self, llm_service_protocol: LLMService) -> None:
        self.llm_service_protocol = llm_service_protocol

    """one interface for all services"""

    def process_query(self, messages: list[dict[str, str]] | None = None) -> str:
        messages = messages or []
        return self.llm_service_protocol.process_query(messages)
