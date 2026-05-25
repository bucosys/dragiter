import logging
from datetime import datetime

from dragiter.domain.models.extended_message import ExtendedMessage
from dragiter.domain.models.chat_message import ChatMessages, ChatMessage

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field

@dataclass(frozen=True)
class ConversationHistory:
    """Immutable container content list"""
    message_extensions: list[ExtendedMessage] = field(default_factory=list)


    def update_assistant_content(self, content: str) -> None:
        for m in self.message_extensions:
            if m.processed_at is None and m.type == 'R':
                m.processed_at = datetime.now()
                m.content = content
                break


    def build_chat_prompt_dict_list(self) -> list[dict]:
        # convenience method to generate next chat query for openai-query
        # get next messages for prompting ai, be patient,
        # call sets processes_at datetime, so call is not repeatable
        # TODO: introduce exceptions
        chat_messages: list[dict[str, str]] = []
        current_time: datetime = datetime.now()

        # check if list not empty and last element (should be a response but we didn't check this) ist processed then ...
        if self.message_extensions and self.message_extensions[-1].type == 'R' and self.message_extensions[-1].processed_at is not None:
            return chat_messages # ... we return an empty list


        for m in self.message_extensions:
            if m.type == 'R' and m.processed_at is None:
                break

            if m.reuse == True or m.processed_at is None:
                chat_messages.append({"role": m.role, "content": m.content})
                m.processed_at = current_time

        return chat_messages


    def generate_chat_messages_list(self) -> list[ChatMessages]:
        # convenience method to generate a list of all input messages (Class ChatMessages) for all chats        # TODO: introduce exceptions
        chat_input_messages: list[ChatMessages] = []
        current_chat_messages: ChatMessages = ChatMessages()

        for m in self.message_extensions:
            if m.type == 'R':
                current_chat_messages.chat_message_list.append(ChatMessage(m.role, m.content))
                chat_input_messages.append(current_chat_messages)       #store last one
                current_chat_messages: ChatMessages = ChatMessages()    #new one
            else:
                current_chat_messages.chat_message_list.append(ChatMessage(m.role, m.content))

        return chat_input_messages


    def __repr__(self):
        # Das hier wird im Logger angezeigt
        return f"ConversationHistory(ExtendedMessenge length ='{len(self.message_extensions)}'"



class ConversionHistoryError(Exception):
    pass