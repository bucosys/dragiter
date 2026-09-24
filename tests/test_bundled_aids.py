# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""Tests for the bundled aids: InfoPresenter, ResourceExporter and cli.py's pre-selector."""

from __future__ import annotations

import importlib.resources
from pathlib import Path
import sys

import pytest

from dragiter import cli
from dragiter.application.config.configuration_loader import ConfigurationLoader
from dragiter.infrastructure.cli.info_presenter import InfoPresenter
from dragiter.infrastructure.cli.resource_exporter import ResourceExporter


def _fake_files(root: Path):
    """Return a stand-in for importlib.resources.files('dragiter') rooted at `root`."""

    def _files(package: str) -> Path:
        assert package == "dragiter"
        return root

    return _files


def _forbid_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if the pre-selector falls through into the real pipeline."""

    def _boom(*_args, **_kwargs):
        raise AssertionError("pipeline reached; pre-selector should have returned first")

    monkeypatch.setattr(ConfigurationLoader, "run", _boom)


class TestNoArgumentBanner:
    """Covers HELP-01."""

    def test_no_arguments_prints_banner_and_usage_and_returns_0(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["dragiter"])
        _forbid_pipeline(monkeypatch)

        rc = cli.main()

        assert rc == 0
        out = capsys.readouterr().out
        assert "Deterministic Context Iterator" in out
        assert "Usage: dragiter" in out
        assert "dragiter --info" in out
        assert "dragiter-gen-docs" in out
        assert "dragiter-gen-examples" in out


class TestInfoSwitch:
    """Covers HELP-02, HELP-03."""

    @pytest.mark.parametrize("flag", ["--info", "-info", "/info", "--INFO"])
    def test_info_switch_prints_packaged_text_and_returns_0(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, flag: str
    ) -> None:
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "info.txt").write_text("DRAGITER MANUAL PAGE\n", encoding="utf-8")
        monkeypatch.setattr(importlib.resources, "files", _fake_files(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["dragiter", flag])
        _forbid_pipeline(monkeypatch)

        rc = cli.main()

        assert rc == 0
        assert "DRAGITER MANUAL PAGE" in capsys.readouterr().out

    def test_info_switch_any_position_is_recognised(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
    ) -> None:
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "info.txt").write_text("MANUAL\n", encoding="utf-8")
        monkeypatch.setattr(importlib.resources, "files", _fake_files(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["dragiter", "-p", "task.md", "--info"])
        _forbid_pipeline(monkeypatch)

        rc = cli.main()

        assert rc == 0
        assert "MANUAL" in capsys.readouterr().out

    def test_missing_info_resource_prints_error_and_returns_1(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
    ) -> None:
        # tmp_path has no docs/info.txt at all -> read_text() raises.
        monkeypatch.setattr(importlib.resources, "files", _fake_files(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["dragiter", "--info"])
        _forbid_pipeline(monkeypatch)

        rc = cli.main()

        assert rc == 1
        assert "Error loading help:" in capsys.readouterr().out


class TestHelpFlag:
    """Covers HELP-04."""

    def test_help_flag_prints_argparse_help_and_exits_0(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["dragiter", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            cli.main()

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "Deterministic Context Iterator" in out
        assert "--output-file" in out
        assert "--version" in out


class TestResourceExporterHappyPath:
    """Covers HELP-05, HELP-06, HELP-07."""

    def _fake_package_root(self, tmp_path: Path) -> Path:
        pkg_root = tmp_path / "pkg"
        (pkg_root / "docs").mkdir(parents=True)
        (pkg_root / "docs" / "manual.md").write_text("manual", encoding="utf-8")
        (pkg_root / "examples").mkdir(parents=True)
        (pkg_root / "examples" / "sample.toml").write_text("sample", encoding="utf-8")
        return pkg_root

    def test_gen_docs_no_path_exports_to_cwd(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
    ) -> None:
        pkg_root = self._fake_package_root(tmp_path)
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        monkeypatch.setattr(importlib.resources, "files", _fake_files(pkg_root))
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "argv", ["dragiter-gen-docs"])

        cli.gen_docs()

        assert (cwd / "docs" / "manual.md").read_text(encoding="utf-8") == "manual"
        out = capsys.readouterr().out
        assert "✅" in out
        assert "successfully exported" in out

    def test_gen_docs_with_path_merges_into_existing_directory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        pkg_root = self._fake_package_root(tmp_path)
        target = tmp_path / "target"
        (target / "docs").mkdir(parents=True)
        (target / "docs" / "pre-existing.md").write_text("kept", encoding="utf-8")
        monkeypatch.setattr(importlib.resources, "files", _fake_files(pkg_root))
        monkeypatch.setattr(sys, "argv", ["dragiter-gen-docs", str(target)])

        cli.gen_docs()

        assert (target / "docs" / "manual.md").read_text(encoding="utf-8") == "manual"
        assert (target / "docs" / "pre-existing.md").read_text(encoding="utf-8") == "kept"

    def test_gen_examples_analogous_to_gen_docs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        pkg_root = self._fake_package_root(tmp_path)
        target = tmp_path / "target2"
        monkeypatch.setattr(importlib.resources, "files", _fake_files(pkg_root))
        monkeypatch.setattr(sys, "argv", ["dragiter-gen-examples", str(target)])

        cli.gen_examples()

        assert (target / "examples" / "sample.toml").read_text(encoding="utf-8") == "sample"


class TestResourceExporterMissingResource:
    """Covers HELP-08."""

    def test_missing_packaged_resource_prints_error_and_exits_1(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
    ) -> None:
        empty_pkg_root = tmp_path / "empty_pkg"
        empty_pkg_root.mkdir()
        monkeypatch.setattr(importlib.resources, "files", _fake_files(empty_pkg_root))
        monkeypatch.setattr(sys, "argv", ["dragiter-gen-docs", str(tmp_path / "out")])

        with pytest.raises(SystemExit) as exc_info:
            ResourceExporter.export("docs")

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "❌" in err
        assert "not found in package" in err


class TestInfoPresenterDirect:
    """Direct unit coverage for InfoPresenter, independent of the cli.py pre-selector."""

    def test_show_usage_returns_0(self, capsys) -> None:
        assert InfoPresenter.show_usage() == 0
        assert "Usage: dragiter" in capsys.readouterr().out

    def test_print_banner_never_raises_and_prints_version(self, capsys) -> None:
        InfoPresenter.print_banner()
        assert "dragiter v" in capsys.readouterr().out
