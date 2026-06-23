import json
import textwrap

from dragiter.application.core.xdi import *
from dragiter.domain.models.chat_sessions import ChatMessage
from dragiter.domain.models.chat_sessions import ChatSessions, ChatSession
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.settings import VerboseBoolSetting

logger = logging.getLogger(__name__)


class MessageBuilder:

    def _create_chat_message_list(self, chat_sessions: ChatSessions) -> list[ChatMessage]:
        chat_message_list: list[ChatMessage] = []
        for chat_session in chat_sessions.session_list:
            chat_message_list.extend(chat_session.input_chat_message_list)

        return chat_message_list  # --->

    def _createChatSession(
            self,
            prompt: PromptTemplate,
            dict_line: dict | None,
            *chunks: Chunk
    ) -> ChatSession:
        cs: ChatSession = ChatSession()

        # 1. System Instruction
        if prompt.instruction is not None:
            cs.input_chat_message_list.append(
                ChatMessage(role="system", content=prompt.instruction)
            )

        # 2. First / Introduction
        if prompt.first is not None:
            cs.input_chat_message_list.append(
                ChatMessage(role="user", content=prompt.first)
            )

        # 3. Material / Chunks
        if chunks:
            for chunk in chunks:
                material_with_chunk = chunk.format_template(prompt.material)
                cs.input_chat_message_list.append(
                    ChatMessage(role="user", content=material_with_chunk)
                )
        elif prompt.material is not None:
            cs.input_chat_message_list.append(
                ChatMessage(role="user", content=prompt.material)
            )

        # 4. Synthesis mit Platzhalter-Ersetzung
        if prompt.synthesis is not None:
            if dict_line:
                try:
                    formatted_synthesis = prompt.synthesis.format_map(dict_line)
                except KeyError as e:
                    # Warnung ausgeben, wenn Platzhalter nicht ersetzt werden konnten
                    logger.warning(
                        f"Some placeholders in synthesis could not be replaced: {e}. "
                        f"Using raw synthesis without formatting for this iteration."
                    )
                    formatted_synthesis = prompt.synthesis

                cs.input_chat_message_list.append(
                    ChatMessage(role="user", content=formatted_synthesis)
                )
            else:
                cs.input_chat_message_list.append(
                    ChatMessage(role="user", content=prompt.synthesis)
                )

        return cs


    def run(self,
            material: Material,
            prompt: PromptTemplate,
            loop: Loop,
            verbose_setting: VerboseBoolSetting
            ) -> ChatSessions:

        # me_list: list[ExtendedMessage] = []

        chat_sessions: ChatSessions = ChatSessions()

        if prompt.sequential_processing:

            # iter chunks, create a session for every single chunk
            for chunk in material.chunks:

                # branch a - loop lines exist
                for dict_line in loop.lines:
                    # we start with a new ChatSession
                    cs: ChatSession = self._createChatSession(prompt, dict_line, chunk)
                    if cs:
                        cs.chunk = chunk
                        cs.loop_item = dict_line
                        chat_sessions.session_list.append(cs)

                # branch b - no lines
                if len(loop.lines) == 0:
                    cs: ChatSession = self._createChatSession(prompt, None, chunk)
                    if cs:
                        cs.chunk = chunk
                        chat_sessions.session_list.append(cs)

        else:
            # do not iter chunks, create one session for all chunks
            # by contract there must be an empty element in content

            # branch a - loop lines exist
            for dict_line in loop.lines:
                cs: ChatSession = self._createChatSession(prompt, dict_line, *material.chunks)
                if cs:
                    cs.chunk = material.chunks[-1] if material.chunks else None
                    cs.loop_item = dict_line
                    chat_sessions.session_list.append(cs)

            # branch b - no lines
            if len(loop.lines) == 0:
                cs: ChatSession = self._createChatSession(prompt, None, *material.chunks)
                if cs:
                    cs.chunk = material.chunks[-1] if material.chunks else None
                    chat_sessions.session_list.append(cs)

        # final: debuglog and return
        if verbose_setting.value:
            cm_flat_list: list[ChatMessage] = self._create_chat_message_list(chat_sessions)
            for icounter, m in enumerate(cm_flat_list, start=1):
                logger.debug(
                    json.dumps({
                        "#": f"{icounter:04}",
                        "RL": m.role,
                        "CT": textwrap.shorten(m.content or "", width=100, placeholder="...")}))

        return chat_sessions


class MessageBuilderError(Exception):
    pass
