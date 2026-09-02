# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dataclasses import fields
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
