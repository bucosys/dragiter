# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

"""Unit tests for PromptCreator's built-in defaults and CLI-override
precedence, and for the unknown-placeholder failure mode when a chunk's
material template is formatted (see MessageBuilder/Chunk.format_template).

Stdin handling is covered separately in tests/test_prompt_creator_stdin.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from support import blank_parameter_groups

from dragiter.application.pipeline.prompt_creator import PromptCreator
from dragiter.domain.models.chunk import Chunk
from dragiter.domain.models.settings import ValueOrigin

_MINIMAL_PROMPT = """\
[system]
instruction = "Be brief."

[task]
first = "Use the following material:"
material = "{CHUNK_CONTENT}"
synthesis = "{LOOP_CONTENT}"
"""

_PROMPT_WITH_BEHAVIOUR_AND_OUTCOME = """\
[system]
instruction = "Be brief."

[task]
first = "Use the following material:"
material = "{CHUNK_CONTENT}"
synthesis = "{LOOP_CONTENT}"

[behaviour]
temperature = 0.7
sequential_processing = true

[outcome]
output_delimiter = "---"
output_filename_schema = "{CHUNK_FILE_NAME}.md"
"""


def _groups_with_prompt_file(tmp_path: Path, text: str):
    groups = blank_parameter_groups()
    prompt = tmp_path / "prompt.toml"
    prompt.write_text(text, encoding="utf-8")
    groups["ip"].prompt_file_path_setting.set(prompt, ValueOrigin.CLI)
    return groups


def _run(groups):
    return PromptCreator().run(groups["ip"], groups["ep"], groups["op"], groups["aisp"])


def test_missing_behaviour_and_outcome_keys_take_builtin_defaults(
    tmp_path: Path,
) -> None:
    """Covers PRMT-06."""
    template = _run(_groups_with_prompt_file(tmp_path, _MINIMAL_PROMPT))

    assert template.temperature == 0.0
    assert template.sequential_processing is False
    assert template.output_filename_schema == "dragiter-out.txt"
    assert template.output_delimiter == "\n"


def test_cli_flags_override_file_values_field_by_field(tmp_path: Path) -> None:
    """Covers PRMT-07."""
    groups = _groups_with_prompt_file(tmp_path, _PROMPT_WITH_BEHAVIOUR_AND_OUTCOME)
    groups["ep"].sequential_processing_bool_setting.set(False, ValueOrigin.CLI)
    groups["op"].output_delimiter_string_setting.set("###", ValueOrigin.CLI)
    groups["op"].output_filename_schema_string_setting.set(
        "result.txt", ValueOrigin.CLI
    )
    groups["aisp"].temperature_float_setting.set(0.1, ValueOrigin.CLI)

    template = _run(groups)

    assert template.sequential_processing is False
    assert template.output_delimiter == "###"
    assert template.output_filename_schema == "result.txt"
    assert template.temperature == pytest.approx(0.1)


def test_file_value_is_kept_when_the_matching_cli_flag_is_not_set(
    tmp_path: Path,
) -> None:
    """Covers PRMT-07: only the fields with an explicit CLI flag are overridden."""
    groups = _groups_with_prompt_file(tmp_path, _PROMPT_WITH_BEHAVIOUR_AND_OUTCOME)
    groups["op"].output_delimiter_string_setting.set("###", ValueOrigin.CLI)
    # sequential_processing, output_filename_schema and temperature are left unset.

    template = _run(groups)

    assert template.output_delimiter == "###"
    assert template.sequential_processing is True
    assert template.output_filename_schema == "{CHUNK_FILE_NAME}.md"
    assert template.temperature == pytest.approx(0.7)


def test_unknown_placeholder_in_material_template_raises_key_error() -> None:
    """Covers PRMT-08."""
    chunk = Chunk(
        num_id=1,
        filename="note.md",
        section_name="sec01",
        section_num_id=1,
        valid=True,
        content="hello",
    )

    with pytest.raises(KeyError):
        chunk.format_template("{NOT_A_REAL_PLACEHOLDER}")
