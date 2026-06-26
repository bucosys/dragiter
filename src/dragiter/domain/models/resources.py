import logging

from dragiter.domain.models.text_file import TextFile

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


class Resources():
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


class ResourceSectionError(Exception):
    pass


class ResourcesError(Exception):
    pass
