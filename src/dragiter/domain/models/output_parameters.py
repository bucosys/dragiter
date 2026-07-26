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
from dataclasses import dataclass

from dragiter.domain.models.settings import (
    OutputDirectoryPathSetting,
    ActivityFilePathSetting, LogFilePathSetting, OutputFilePathSetting,
    OutputDelimiterStringSetting, OutputFilenameSchemaStringSetting, OutputModeStringSetting)
from dragiter.domain.models.value_settings_activity_provider import ValueSettingsActivityProvider


@dataclass(frozen=True)
class OutputParameters(ValueSettingsActivityProvider):
    output_delimiter_string_setting: OutputDelimiterStringSetting
    output_filename_schema_string_setting: OutputFilenameSchemaStringSetting
    output_mode_string_setting: OutputModeStringSetting
    activity_file_path_setting: ActivityFilePathSetting
    logfile_path_setting: LogFilePathSetting
    output_directory_path_setting: OutputDirectoryPathSetting
    output_file_path_setting: OutputFilePathSetting



