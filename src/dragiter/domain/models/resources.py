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

import logging
from typing import Any

from dragiter.domain.models.text_file import TextFile
from dragiter.domain.ports.activity_provider import ActivityProvider

logger = logging.getLogger(__name__)


class ResourceSection():

    def __init__(self, section_name: str, text_files: list[TextFile], regex_pattern: str, exclude_filters: list[str],
                 include_filters: list[str]) -> None:
        """Initialise the configuration object and load settings."""

        # member
        self._file_paths: list[TextFile] = []

        # params
        if not section_name or section_name.strip() == "":
            raise ResourceSectionError("Section name cannot be None or empty string.")

        self._section_name: str = section_name

        if text_files:
            self._file_paths.extend(text_files)

        self._regex_pattern: str = regex_pattern or "(?!)"
        self._exclude_filters: list[str] = exclude_filters or []
        self._include_filters: list[str] = include_filters or []

    @property
    def file_paths(self) -> list[TextFile]:
        return self._file_paths

    @property
    def section_name(self) -> str:
        return self._section_name

    @property
    def regex_pattern(self) -> str:
        return self._regex_pattern

    @property
    def exclude_filters(self) -> list[str]:
        return self._exclude_filters

    @property
    def include_filters(self) -> list[str]:
        return self._include_filters

    def __repr__(self):
        # Das hier wird im Logger angezeigt
        return f"ResourceSection(files length ='{len(self._file_paths)}'"


class Resources(ActivityProvider):
    def __init__(self):
        """Initialise the configuration object and load settings."""
        self._resource_sections: list[ResourceSection] = []

    @property
    def resource_sections(self) -> list[ResourceSection]:
        return self._resource_sections[:]

    def append_resource_section(self, new_value: ResourceSection) -> ResourceSection:
        # if new_value is None:
        #     raise ResourcesError("ResourceSection cannot be None.")

        # if not new_value.section_name or new_value.section_name.strip() == "":
        #     raise ResourcesError("Section name cannot be None or empty string.")

        # if any(section.section_name == new_value.section_name
        #        for section in self._resource_sections):
        #     raise ResourcesError("Value has already been set and cannot be changed!")

        self._resource_sections.append(new_value)

        return new_value

    def __repr__(self):
        # This is shown in the logger
        return f"Resources(ResourceSection length ='{len(self._resource_sections)}'"

    def to_activity_dict_list(self) -> list[dict[str, Any]]:
        """
        Provides detailed activity information about loaded resources for auditing.
        Uses aggregation to prevent log bloat with very large file sets.
        """
        total_files = sum(len(section.file_paths) for section in self._resource_sections)

        activity_dict: dict[str, Any] = {
            "resource_sections_count": len(self._resource_sections),
            "total_files": total_files,
        }

        sections_details = []
        detailed_files_count = 0

        for section in self._resource_sections:
            file_count = len(section.file_paths)
            file_paths = [str(tf.path) for tf in section.file_paths]

            files_info = file_count

            section_info = {
                "section_name": section.section_name,
                "file_count": file_count,
                "regex_pattern": section.regex_pattern,
                "exclude_filters": section.exclude_filters,
                "include_filters": section.include_filters,
                "files": files_info
            }
            sections_details.append(section_info)

        activity_dict["sections"] = sections_details

        logger.debug(f"Resources activity: {len(self._resource_sections)} section(s), "
                     f"{total_files} files total "
                     f"({detailed_files_count} files listed in detail)")

        return [activity_dict]

class ResourceSectionError(Exception):
    pass


class ResourcesError(Exception):
    pass
