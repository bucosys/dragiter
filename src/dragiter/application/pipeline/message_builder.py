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

import json
import re
import textwrap
from collections import defaultdict

from dragiter.application.core.xdi import *
from dragiter.domain.models.chat_sessions import ChatMessage, ChatSessions, ChatSession
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.settings import VerboseBoolSetting

logger = logging.getLogger(__name__)


class MessageBuilder:
    """Builds chat sessions from prompts, materials, and loop data."""

    def _extract_placeholders(self, text: str) -> list[str]:
        """Extract all placeholder names of the form {name} from a string."""
        if not text:
            return []
        return re.findall(r"\{(\w+)\}", text)

    def _create_chat_message_list(self, chat_sessions: ChatSessions) -> list[ChatMessage]:
        """Flatten all input messages from all chat sessions (used for verbose logging)."""
        chat_message_list: list[ChatMessage] = []
        for chat_session in chat_sessions.session_list:
            chat_message_list.extend(chat_session.input_chat_message_list)
        return chat_message_list

    def _create_chat_session(
        self,
        prompt: PromptTemplate,
        dict_line: dict | None,
        *chunks: Chunk
    ) -> ChatSession:
        """Create a single ChatSession with system, material, and synthesis messages."""
        cs = ChatSession()

        # 1. System instruction
        if prompt.instruction is not None:
            cs.input_chat_message_list.append(
                ChatMessage(role="system", content=prompt.instruction)
            )

        # 2. First / introductory message
        if prompt.first is not None:
            cs.input_chat_message_list.append(
                ChatMessage(role="user", content=prompt.first)
            )

        # 3. Material chunks
        if chunks:
            for chunk in chunks:
                formatted_material = chunk.format_template(prompt.material)
                cs.input_chat_message_list.append(
                    ChatMessage(role="user", content=formatted_material)
                )
        elif prompt.material is not None:
            cs.input_chat_message_list.append(
                ChatMessage(role="user", content=prompt.material)
            )

        # 4. Synthesis with safe placeholder replacement
        if prompt.synthesis is not None:
            if dict_line:
                # Use defaultdict so missing keys remain visible as {key}
                safe_dict = defaultdict(lambda key: "{" + key + "}", dict_line)
                formatted_synthesis = prompt.synthesis.format_map(safe_dict)

                # Detect which placeholders could not be replaced
                expected_keys = self._extract_placeholders(prompt.synthesis)
                missing_keys = [key for key in expected_keys if key not in dict_line]

                if missing_keys:
                    logger.warning(
                        f"Some placeholders in synthesis could not be replaced: {missing_keys}. "
                        f"These placeholders remain unchanged in the output."
                    )

                cs.input_chat_message_list.append(
                    ChatMessage(role="user", content=formatted_synthesis)
                )
            else:
                cs.input_chat_message_list.append(
                    ChatMessage(role="user", content=prompt.synthesis)
                )

        return cs

    def run(
        self,
        material: Material,
        prompt: PromptTemplate,
        loop: Loop,
        verbose_setting: VerboseBoolSetting
    ) -> ChatSessions:
        """Build all chat sessions based on material, prompt, and loop configuration."""
        chat_sessions = ChatSessions()

        if prompt.sequential_processing:
            # Process each chunk individually
            for chunk in material.chunks:
                for dict_line in loop.lines:
                    cs = self._create_chat_session(prompt, dict_line, chunk)
                    cs.chunk = chunk
                    cs.loop_item = dict_line
                    chat_sessions.session_list.append(cs)

                if not loop.lines:
                    cs = self._create_chat_session(prompt, None, chunk)
                    cs.chunk = chunk
                    chat_sessions.session_list.append(cs)
        else:
            # Process all chunks together in one session
            for dict_line in loop.lines:
                cs = self._create_chat_session(prompt, dict_line, *material.chunks)
                cs.chunk = material.chunks[-1] if material.chunks else None
                cs.loop_item = dict_line
                chat_sessions.session_list.append(cs)

            if not loop.lines:
                cs = self._create_chat_session(prompt, None, *material.chunks)
                cs.chunk = material.chunks[-1] if material.chunks else None
                chat_sessions.session_list.append(cs)

        # Verbose debug logging
        if verbose_setting.value:
            flat_messages = self._create_chat_message_list(chat_sessions)
            for index, message in enumerate(flat_messages, start=1):
                logger.debug(
                    json.dumps({
                        "#": f"{index:04}",
                        "RL": message.role,
                        "CT": textwrap.shorten(message.content or "", width=100, placeholder="...")
                    })
                )

        return chat_sessions


class MessageBuilderError(Exception):
    """Raised when message building fails."""
    pass