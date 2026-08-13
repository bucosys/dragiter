# =============================================================================
# dragiter - Deterministic Context Iterator
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
from dataclasses import dataclass

from dragiter.domain.models.settings import (
    BaseDirectoryPathSetting, LoopFilePathSetting, ResourceFilePathSetting, ConfigFilePathSetting,
    PromptFilePathSetting)
from dragiter.domain.models.value_settings_activity_provider import ValueSettingsActivityProvider


@dataclass(frozen=True)
class InputPathParameters(ValueSettingsActivityProvider):
    base_directory_path_setting: BaseDirectoryPathSetting
    config_file_path_setting: ConfigFilePathSetting
    loop_file_path_setting: LoopFilePathSetting
    prompt_file_path_setting: PromptFilePathSetting
    resource_file_path_setting: ResourceFilePathSetting


