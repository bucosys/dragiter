# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import logging
from typing import Any

from dragiter.domain.models.text_file import TextFile
from dragiter.domain.ports.activity_provider import ActivityProvider

logger = logging.getLogger(__name__)


class ResourceSection:
    def __init__(
        self,
        section_name: str,
        text_files: list[TextFile],
        exclude_filters: list[str],
        include_filters: list[str],
        regex_patterns: list[str] | str | None = None,
        pack_limit_chars: int | None = None,
    ) -> None:
        """Initialise the configuration object and load settings."""

        # member
        self._file_paths: list[TextFile] = []

        # params
        if not section_name or section_name.strip() == "":
            raise ResourceSectionError("Section name cannot be None or empty string.")

        self._section_name: str = section_name

        if text_files:
            self._file_paths.extend(text_files)

        self._regex_patterns: list[str] = self._coerce_regex_patterns(regex_patterns)
        self._exclude_filters: list[str] = exclude_filters or []
        self._include_filters: list[str] = include_filters or []
        self._pack_limit_chars: int | None = pack_limit_chars if isinstance(pack_limit_chars, int) else None

    @property
    def file_paths(self) -> list[TextFile]:
        return self._file_paths

    @property
    def section_name(self) -> str:
        return self._section_name

    @property
    def regex_patterns(self) -> list[str]:
        return self._regex_patterns[:]

    @staticmethod
    def _coerce_regex_patterns(
        regex_patterns: list[str] | str | None,
    ) -> list[str]:
        raw: list[object]
        if regex_patterns is None:
            raw = []
        elif isinstance(regex_patterns, str):
            raw = [regex_patterns]
        elif isinstance(regex_patterns, list):
            raw = list(regex_patterns)
        else:
            raise ResourceSectionError("regex_patterns must be a string or a list of strings.")

        cleaned = [item for item in raw if isinstance(item, str) and item != ""]
        return cleaned or ["(?!)"]

    @property
    def exclude_filters(self) -> list[str]:
        return self._exclude_filters

    @property
    def include_filters(self) -> list[str]:
        return self._include_filters

    @property
    def pack_limit_chars(self) -> int | None:
        return self._pack_limit_chars

    def __repr__(self):
        # Displayed in the logger output
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
        total_files = sum(
            len(section.file_paths) for section in self._resource_sections
        )

        activity_dict: dict[str, Any] = {
            "resource_sections_count": len(self._resource_sections),
            "total_files": total_files,
        }

        sections_details: list[dict[str, Any]] = []

        for section in self._resource_sections:
            section_info = {
                "section_name": section.section_name,
                "file_count": len(section.file_paths),
                "regex_patterns": section.regex_patterns,
                "exclude_filters": section.exclude_filters,
                "include_filters": section.include_filters,
                "pack_limit_chars": section.pack_limit_chars,
            }
            sections_details.append(section_info)

        activity_dict["sections"] = sections_details
        return [activity_dict]


class ResourceSectionError(Exception):
    pass


class ResourcesError(Exception):
    pass
