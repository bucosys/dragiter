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
