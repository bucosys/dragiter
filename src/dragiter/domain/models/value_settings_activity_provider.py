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
import datetime
from dataclasses import dataclass, fields
from typing import Any

from dragiter.domain.models.settings import ValueSetting
from dragiter.domain.ports.activity_provider import ActivityProvider

class ValueSettingsActivityProvider(ActivityProvider):


    def _get_safe_value_or_na(self, setting: ValueSetting) -> dict[str, Any]:
        """Returns a {key: value} dict. Masks the value if requested."""

        value = "***MASKED***" if "key" in setting.key else setting.value
        return {setting.key: value}

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        activity_dict: dict[str, Any] = {}

        # dry principle dynamic iteration
        for field in fields(self):
            setting_instance = getattr(self, field.name)

            # append data w/ update method
            if isinstance(setting_instance, ValueSetting):
                activity_dict.update(self._get_safe_value_or_na(setting_instance))

        # must be a list
        return [activity_dict]