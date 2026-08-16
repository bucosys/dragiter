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

"""
Security tests for ResourceCollector path containment.

Relative glob patterns must not be allowed to reach files outside the
configured base directory (classic path-traversal / symlink escape).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dragiter.application.pipeline.resource_collector import ResourceCollector
from dragiter.domain.models.settings import (
    BaseDirectoryPathSetting,
    ResourceFilePathSetting,
)


class _AcceptAllChecker:
    """FileChecker stand-in that treats every path as UTF-8 text."""

    def detect_encoding(self, path: Path) -> str:
        return "utf-8"


def _write_resource_toml(path: Path, patterns: list[str]) -> None:
    lines = ['[config01]', f"glob_patterns = {patterns!r}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _settings(base: Path, resource_toml: Path) -> tuple[ResourceFilePathSetting, BaseDirectoryPathSetting]:
    res = ResourceFilePathSetting(_key="resource_file")
    res.value = resource_toml
    base_setting = BaseDirectoryPathSetting(_key="base_directory")
    base_setting.value = base
    return res, base_setting


class TestResourceCollectorPathEscape:
    def test_symlink_pointing_outside_base_is_skipped(self, tmp_path: Path) -> None:
        """
        A symlink inside the base directory that resolves outside must not
        appear in the collected resources.
        """
        base = tmp_path / "project"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        safe = base / "safe.md"
        safe.write_text("# safe material\n", encoding="utf-8")

        secret = outside / "secret.md"
        secret.write_text("# TOP SECRET\n", encoding="utf-8")

        evil_link = base / "evil.md"
        evil_link.symlink_to(secret)

        resource_toml = base / "resources.toml"
        _write_resource_toml(resource_toml, ["*.md"])

        collector = ResourceCollector(file_checker=_AcceptAllChecker())
        resources = collector.run(*_settings(base, resource_toml))

        collected_paths = {
            tf.path.resolve()
            for section in resources.resource_sections
            for tf in section.file_paths
        }

        assert safe.resolve() in collected_paths
        assert secret.resolve() not in collected_paths
        # The symlink path itself must not survive either (resolved form is outside).
        assert all(base.resolve() in p.parents or p == base.resolve() for p in collected_paths)

    def test_relative_parent_glob_cannot_escape_base(self, tmp_path: Path) -> None:
        """
        Glob patterns containing '..' must not pull in files outside base.
        """
        base = tmp_path / "project"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        safe = base / "safe.md"
        safe.write_text("# safe\n", encoding="utf-8")
        secret = outside / "secret.md"
        secret.write_text("# secret\n", encoding="utf-8")

        resource_toml = base / "resources.toml"
        # Attempt to walk out of base via relative parent references.
        _write_resource_toml(resource_toml, ["../outside/*.md", "*.md"])

        collector = ResourceCollector(file_checker=_AcceptAllChecker())
        resources = collector.run(*_settings(base, resource_toml))

        collected_paths = {
            tf.path.resolve()
            for section in resources.resource_sections
            for tf in section.file_paths
        }

        assert safe.resolve() in collected_paths
        assert secret.resolve() not in collected_paths

    def test_legitimate_nested_file_is_collected(self, tmp_path: Path) -> None:
        """Sanity check: normal nested files inside base are still found."""
        base = tmp_path / "project"
        nested = base / "docs"
        nested.mkdir(parents=True)
        target = nested / "note.md"
        target.write_text("# note\n", encoding="utf-8")

        resource_toml = base / "resources.toml"
        _write_resource_toml(resource_toml, ["docs/**/*.md"])

        collector = ResourceCollector(file_checker=_AcceptAllChecker())
        resources = collector.run(*_settings(base, resource_toml))

        collected_paths = {
            tf.path.resolve()
            for section in resources.resource_sections
            for tf in section.file_paths
        }

        assert target.resolve() in collected_paths
