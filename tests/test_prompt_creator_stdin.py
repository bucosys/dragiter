# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""
Regression tests for PromptCreator stdin handling.

Stdin must be read only when the contract requires it:
``-t`` / ``--task``, or a ``{STDIN}`` placeholder in ``task.first``.
An eager ``sys.stdin.read()`` on a non-TTY that never reaches EOF
hangs the process (CI, systemd, Docker without ``-i``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from support import blank_parameter_groups

from dragiter.application.pipeline import prompt_creator as prompt_creator_mod
from dragiter.application.pipeline.prompt_creator import PromptCreator
from dragiter.domain.models.settings import ValueOrigin
from dragiter.infrastructure.io import io_services

_PROMPT_WITHOUT_STDIN = """\
[system]
instruction = "Be brief."

[task]
first = "Use the following material:"
material = "{CHUNK_CONTENT}"
synthesis = "{LOOP_CONTENT}"
"""

_PROMPT_WITH_STDIN = """\
[system]
instruction = "Be brief."

[task]
first = "Preamble:\\n{STDIN}\\n---"
material = "{CHUNK_CONTENT}"
synthesis = "{LOOP_CONTENT}"
"""


class _BlockingStdin:
    """Stand-in for an inherited, still-open non-TTY stdin."""

    def isatty(self) -> bool:
        return False

    def read(self, size: int = -1) -> str:
        raise AssertionError(
            "stdin.read() must not be called unless {STDIN} or -t is in use"
        )


def _groups(
    tmp_path: Path,
    *,
    prompt_text: str | None = None,
    task: str | None = None,
):
    groups = blank_parameter_groups()
    if task is not None:
        groups["ip"].task_string_setting.set(task, ValueOrigin.CLI)
    if prompt_text is not None:
        prompt = tmp_path / "prompt.toml"
        prompt.write_text(prompt_text, encoding="utf-8")
        groups["ip"].prompt_file_path_setting.set(prompt, ValueOrigin.CLI)
    return groups


def _run(groups):
    return PromptCreator().run(
        groups["ip"], groups["ep"], groups["op"], groups["aisp"]
    )


def test_prompt_file_without_placeholder_does_not_read_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Smoke path: -p without {STDIN} must not touch stdin at all."""
    monkeypatch.setattr(io_services.sys, "stdin", _BlockingStdin())
    template = _run(_groups(tmp_path, prompt_text=_PROMPT_WITHOUT_STDIN))
    assert template.first == "Use the following material:"
    assert "{STDIN}" not in (template.first or "")


def test_placeholder_is_replaced_with_piped_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prompt_creator_mod, "read_stdin_content", lambda: "piped payload")
    template = _run(_groups(tmp_path, prompt_text=_PROMPT_WITH_STDIN))
    assert "piped payload" in template.first
    assert "{STDIN}" not in template.first


def test_placeholder_with_empty_stdin_becomes_empty_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prompt_creator_mod, "read_stdin_content", lambda: None)
    template = _run(_groups(tmp_path, prompt_text=_PROMPT_WITH_STDIN))
    assert template.first == "Preamble:\n\n---"


def test_task_flag_reads_stdin_as_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prompt_creator_mod, "read_stdin_content", lambda: "from pipe")
    template = _run(_groups(tmp_path, task="Summarise this."))
    assert template.first == "from pipe"
    assert template.synthesis == "Summarise this."


def test_task_flag_invokes_stdin_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = {"n": 0}

    def _read() -> str:
        called["n"] += 1
        return "x"

    monkeypatch.setattr(prompt_creator_mod, "read_stdin_content", _read)
    _run(_groups(tmp_path, task="Do the work."))
    assert called["n"] == 1


def test_prompt_file_without_placeholder_does_not_call_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _forbidden() -> str:
        raise AssertionError("read_stdin_content must not be called")

    monkeypatch.setattr(prompt_creator_mod, "read_stdin_content", _forbidden)
    _run(_groups(tmp_path, prompt_text=_PROMPT_WITHOUT_STDIN))
