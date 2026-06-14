from dragiter.domain.common.base_validator import BaseValidator
from dragiter.domain.models.chat_sessions import ChatSessions


# ==========================================
# Corresponding validator class V
# ==========================================
class ChatSessionsValidator(BaseValidator[ChatSessions]):
    """
    This validator is strictly bound to the 'SensorData' class.
    """

    def validate_object(self, obj: ChatSessions) -> None:

        if obj is None:
            raise TypeError(f'Object of type {type(obj)} cannot be None')

        if not isinstance(obj, ChatSessions):
            raise TypeError(f'Object of type {type(obj)} wrong type')

        if obj.session_list is None:
            raise TypeError(f'Object of type {type(obj.session_list)} cannot be None')
