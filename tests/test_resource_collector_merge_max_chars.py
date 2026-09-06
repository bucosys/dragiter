# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from __future__ import annotations

from pathlib import Path

from dragiter.application.pipeline.resource_collector import ResourceCollector
from dragiter.domain.models.parameters import InputParameters, WorkspaceParameters
from dragiter.domain.models.settings import (
    BaseDirectoryPathSetting,
    ConfigFilePathSetting,
    LoopFilePathSetting,
    PromptFilePathSetting,
    ResourceFilePathSetting,
    TaskStringSetting,
    ValueOrigin,
)


class _AcceptAllChecker:
    def detect_encoding(self, path: Path) -> str:
        return "utf-8"


def test_resource_toml_pack_limit_chars_is_stored(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    source.write_text("# hi\n", encoding="utf-8")
    resource_toml = tmp_path / "resource.toml"
    resource_toml.write_text(
        "\n".join(
            [
                "[config01]",
                'glob_patterns = ["*.md"]',
                f"base_directory = {str(tmp_path)!r}",
                "pack_limit_chars = 1500",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    res_setting = ResourceFilePathSetting("resource_file")
    res_setting.set(resource_toml, ValueOrigin.CLI)
    base_setting = BaseDirectoryPathSetting("base_directory")
    base_setting.set(tmp_path, ValueOrigin.CLI)
    ip = InputParameters(
        TaskStringSetting("task"),
        PromptFilePathSetting("prompt_file"),
        LoopFilePathSetting("loop_file"),
        res_setting,
    )
    wp = WorkspaceParameters(base_setting, ConfigFilePathSetting("config_file"))

    resources = ResourceCollector(_AcceptAllChecker()).run(ip, wp)

    assert len(resources.resource_sections) == 1
    assert resources.resource_sections[0].pack_limit_chars == 1500
    activity = resources.to_activity_dict_list()[0]
    assert activity["sections"][0]["pack_limit_chars"] == 1500


def test_resource_toml_regex_patterns_list_is_stored(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    source.write_text("# hi\n", encoding="utf-8")
    resource_toml = tmp_path / "resource.toml"
    resource_toml.write_text(
        "\n".join(
            [
                "[config01]",
                'glob_patterns = ["*.md"]',
                f"base_directory = {str(tmp_path)!r}",
                'regex_patterns = ["^#+\\\\s+.*$", "\\\\n\\\\n"]',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    res_setting = ResourceFilePathSetting("resource_file")
    res_setting.set(resource_toml, ValueOrigin.CLI)
    base_setting = BaseDirectoryPathSetting("base_directory")
    base_setting.set(tmp_path, ValueOrigin.CLI)
    ip = InputParameters(
        TaskStringSetting("task"),
        PromptFilePathSetting("prompt_file"),
        LoopFilePathSetting("loop_file"),
        res_setting,
    )
    wp = WorkspaceParameters(base_setting, ConfigFilePathSetting("config_file"))

    resources = ResourceCollector(_AcceptAllChecker()).run(ip, wp)

    assert resources.resource_sections[0].regex_patterns == [r"^#+\s+.*$", r"\n\n"]
    activity = resources.to_activity_dict_list()[0]
    assert activity["sections"][0]["regex_patterns"] == [r"^#+\s+.*$", r"\n\n"]
