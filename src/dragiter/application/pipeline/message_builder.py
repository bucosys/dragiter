import json

from dragiter.domain.models.settings import VerboseBoolSetting
from dragiter.application.core.xdi import *
from dragiter.domain.models.conversation_history import ConversationHistory
from dragiter.domain.models.extended_message import ExtendedMessage
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.material import Material
from dragiter.domain.models.prompt_template import PromptTemplate
import textwrap

logger = logging.getLogger(__name__)

class MessageBuilder:
    def __init__(self) -> None:
        self.simulate: bool = False



    def run(self,
            material: Material,
            prompt: PromptTemplate,
            loop: Loop,
            verbose_setting: VerboseBoolSetting
            ) -> ConversationHistory:

        me_list: list[ExtendedMessage] = []

        answers: list[str] = []

        if prompt.sequential_processing:
            for chunk in material.chunks:
                for dict_line in loop.lines:
                    if prompt.instruction is not None: me_list.append(ExtendedMessage(type="S", role="system", content=prompt.instruction))
                    if prompt.first is not None: me_list.append(ExtendedMessage(type="U", role="user", content=prompt.first))
                    if prompt.material is not None:
                        material_with_chunk = chunk.format_template(prompt.material)
                        me_list.append(ExtendedMessage(type="U", role="user", content=material_with_chunk))


                    if prompt.synthesis is not None:

                        formatted_synthesis = prompt.synthesis

                        if dict_line is not None and len(dict_line.get("LOOP_CONTENT", "")) > 0:
                            # loop_content = loop_element.get("LOOP_CONTENT", "")
                            formatted_synthesis = prompt.synthesis.format_map(dict_line)


                        me_list.append(ExtendedMessage(type="U", role="user", content=formatted_synthesis))
                        me_list.append(ExtendedMessage(type="R", role="assistant", content=None))


                if len(loop.lines) == 0:
                    if prompt.instruction is not None: me_list.append(ExtendedMessage(type="S", role="system", content=prompt.instruction))
                    if prompt.first is not None: me_list.append(ExtendedMessage(type="U", role="user", content=prompt.first))
                    if prompt.material is not None:
                        material_with_chunk = chunk.format_template(prompt.material)
                        me_list.append(ExtendedMessage(type="U", role="user", content=material_with_chunk))


                    if prompt.synthesis is not None:
                        me_list.append(ExtendedMessage(type="U", role="user", content=prompt.synthesis))
                        me_list.append(ExtendedMessage(type="R", role="assistant", content=None))


        else:
            # by contract there must be an empty element in content
            for dict_line in loop.lines:
                if prompt.instruction is not None: me_list.append(
                    ExtendedMessage(type="S", role="system", content=prompt.instruction))
                if prompt.first is not None: me_list.append(
                    ExtendedMessage(type="U", role="user", content=prompt.first))
                if prompt.material is not None:
                    for chunk in material.chunks:
                        material_with_chunk = chunk.format_template(prompt.material)
                        me_list.append(ExtendedMessage(type="U", role="user", content=material_with_chunk))
                    if len(material.chunks) == 0:
                        me_list.append(ExtendedMessage(type="U", role="user", content=prompt.material))

                if prompt.synthesis is not None:
                    formatted_synthesis = prompt.synthesis

                    if dict_line is not None and len(dict_line.get("LOOP_CONTENT", "")) > 0:
                        # loop_content = loop_element.get("LOOP_CONTENT", "")
                        formatted_synthesis = prompt.synthesis.format_map(dict_line)

                    me_list.append(ExtendedMessage(type="U", role="user", content=formatted_synthesis))
                    me_list.append(ExtendedMessage(type="R", role="assistant", content=None))

            if len(loop.lines) == 0:
                if prompt.instruction is not None: me_list.append(
                    ExtendedMessage(type="S", role="system", content=prompt.instruction))
                if prompt.first is not None: me_list.append(
                    ExtendedMessage(type="U", role="user", content=prompt.first))
                if prompt.material is not None:
                    for chunk in material.chunks:
                        material_with_chunk = chunk.format_template(prompt.material)
                        me_list.append(ExtendedMessage(type="U", role="user", content=material_with_chunk))
                    if len(material.chunks) == 0:
                        me_list.append(ExtendedMessage(type="U", role="user", content=prompt.material))

                if prompt.synthesis is not None:
                    me_list.append(ExtendedMessage(type="U", role="user", content=prompt.synthesis))

                me_list.append(ExtendedMessage(type="R", role="assistant", content=None))

        # final: debuglog and return
        if verbose_setting.value:
            for icounter, m in enumerate(me_list, start=1):
                logger.debug(
                    json.dumps({
                        "#": f"{icounter:04}",
                        "TP": m.type,
                        "RL": m.role,
                        "CT": textwrap.shorten(m.content or "", width=100, placeholder="...")}))

        return ConversationHistory(me_list)


    def create_json(self, line: str) -> dict:
        return json.loads(line)

class MessageBuilderError(Exception):
    pass