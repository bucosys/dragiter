# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import logging
from pathlib import Path

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.parameters import InputParameters, WorkspaceParameters
from dragiter.domain.models.resources import Resources, ResourceSection
from dragiter.domain.models.settings import (
    BaseDirectoryPathSetting,
    PathSetting,
    ValueOrigin,
)
from dragiter.domain.models.text_file import TextFile
from dragiter.domain.ports.file_checker import FileChecker
from dragiter.infrastructure.io.io_services import read_from_toml

logger = logging.getLogger(__name__)


class ResourceCollector(Worker):
    def __init__(self, file_checker: FileChecker) -> None:
        self._file_checker = file_checker

    def run(
        self,
        ip: InputParameters,
        wp: WorkspaceParameters,
    ) -> Resources:

        res: Resources = Resources()
        try:
            if ip.resource_file_path_setting.is_set:
                path: Path = ip.resource_file_path_setting.value
                logger.debug(f"Try loading content from file: {path}")
                resource_file_toml_dict = read_from_toml(
                    ip.resource_file_path_setting.value
                )

                for s_name, settings in resource_file_toml_dict.items():
                    if isinstance(settings, dict) and "regex_pattern" in settings:
                        raise MaterialCollectorError(
                            f"Section '{s_name}' uses removed key 'regex_pattern'. "
                            "Replace it with 'regex_patterns' as a list of strings."
                        )
                    text_files: list[TextFile] = []
                    glob_patterns: list[str] = settings.get("glob_patterns") or []
                    base_dir = settings.get("base_directory") or None

                    resource_base_dir = PathSetting()
                    if base_dir:
                        resource_base_dir.set(base_dir, ValueOrigin.CONFIG)
                    else:
                        resource_base_dir.set(Path.cwd().resolve(), ValueOrigin.DEFAULT)

                    if wp.base_directory_path_setting.is_set:
                        resource_base_dir.rebase(wp.base_directory_path_setting.value)



                    if glob_patterns:
                        self._find_valid_textfiles(
                            text_files, glob_patterns, resource_base_dir
                        )

                    if text_files:
                        rs = ResourceSection(
                            section_name=s_name,
                            text_files=text_files,
                            regex_patterns=settings.get("regex_patterns"),
                            exclude_filters=settings.get("exclude_filters"),
                            include_filters=settings.get("include_filters"),
                            pack_limit_chars=settings.get("pack_limit_chars"),
                        )
                        logger.debug(
                            f"Section '{s_name}': {len(text_files)} file(s), "
                            f"{len(rs.regex_patterns)} regex pattern(s), "
                            f"pack_limit_chars={rs.pack_limit_chars}"
                        )
                        res.append_resource_section(rs)

            logger.debug(f"Loaded {res}")
            return res

        except MaterialCollectorError:
            raise
        except Exception as e:
            raise MaterialCollectorError(f"Failed to load material chunks: {e}") from e

    def _find_valid_textfiles(
        self,
        text_files: list[TextFile],
        glob_patterns: list[str],
        base_directory_file_path: BaseDirectoryPathSetting,
    ) -> None:

        root_path = base_directory_file_path.value  # Path.cwd().resolve()

        logger.debug(f"Use root path: {root_path}")

        for pattern in glob_patterns:
            p = Path(pattern)

            logger.debug(f"Use pattern: {p}")

            if p.is_absolute():  # is absolute?
                # Absolute patterns are an explicit, intentional escape hatch:
                # the resource author has written a fully-qualified path themselves,
                # so containment against root_path does not apply here.
                base = Path(p.anchor)  # '/' or 'C:\' etc
                rel_pattern = str(p.relative_to(base))
                matches = list(base.glob(rel_pattern))
                logger.debug(f"(Abs.) Matches: {len(matches)}")
                contained_matches = [m.resolve() for m in matches if m.exists()]
            else:
                matches = list(Path(root_path).glob(pattern))
                logger.debug(f"(Rel.) Matches: {len(matches)}")

                contained_matches = []
                for match in matches:
                    resolved_match = match.resolve()
                    # root path must contain the resolved match; this blocks
                    # patterns like "../../secret" from escaping root_path
                    if (
                        root_path != resolved_match
                        and root_path not in resolved_match.parents
                    ):
                        logger.warning(
                            f"File skipped: {resolved_match} is outside of {root_path}."
                        )
                        continue
                    if resolved_match.exists():
                        contained_matches.append(resolved_match)

            # tidiing section
            absolute_matches = sorted(set(contained_matches))
            valid_files = self._check_matches(absolute_matches)
            text_files.extend(valid_files)

    # remark: absolute paths required !!
    def _check_matches(self, paths: list[Path]) -> list[TextFile]:
        textfiles: list[TextFile] = []
        for path in paths:
            try:
                logger.debug(f"Check encoding: {path}")
                encoding = self._file_checker.detect_encoding(path)
                textfiles.append(TextFile(path, encoding))
            except Exception:
                logger.debug(f"Check failed: {path}")
                continue

        return textfiles


class MaterialCollectorError(Exception):
    pass
