[![License: AGPL v3](https://img.shields.io/badge/License-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![PyPI](https://img.shields.io/pypi/v/dragiter)](https://pypi.org/project/dragiter/)
[![Python](https://img.shields.io/pypi/pyversions/dragiter)](https://pypi.org/project/dragiter/)
[![Website](https://img.shields.io/badge/Website-dragiter.app-blue)](https://dragiter.app)

# dragiter - Deterministic Context Iterator

A focused command-line tool for structured, reproducible LLM workflows.

**Source:** [GitLab](https://gitlab.com/bucosys/dragiter) · [Releases](https://gitlab.com/bucosys/dragiter/-/releases) · [Issues](https://gitlab.com/bucosys/dragiter/-/issues) · [Website](https://dragiter.app)

dragiter treats large language models the way a well-mannered Unix utility treats everything else: as a stage in a
pipeline. You supply material, a prompt template and (optionally) a loop file; it assembles deterministic requests and
writes the results where you tell it to. No chat interface, no hidden state, no surprises.

## Why it exists

Assembling context for an LLM by hand is a peculiar form of digital drudgery. dragiter replaces that ritual with
something closer to proper engineering:

- **Structured context assembly** - glob patterns and regular expressions carve documents into the exact chunks the
  model should see.
- **Prompt templates as code** - system instructions, material formatting and synthesis logic live in plain TOML files
  that can be version-controlled, reviewed and shared.
- **Batch iteration without custom scripts** - a simple text file or JSONL loop drives repeated runs with different
  parameters.
- **Provider independence** - any OpenAI-compatible endpoint (local Ollama, xAI Grok, Google, LiteLLM proxies, …) works
  by changing three settings: `base_url`, `model_name` and `api_key`.

If you prefer deterministic behaviour, explicit file routing and the ability to put an entire AI workflow under version
control, this tool is for you.

## Installation

```bash
pip install dragiter
```

Requires Python ≥ 3.11.

## Compatibility

**2026.9.26 changes output routing.** `-o` and `-O` are now mutually
exclusive (previously both could be set together); the validator rejects the
combination outright. The scratch copies kept while a run is in progress no
longer live under `.dragiter-partial/` - that directory is gone. Each run
now stages its completions in a hidden, sink-specific workspace instead:
`.tmp_staging_dir_<PID>/` inside `-O`'s directory, `.tmp_staging_file_<PID>/`
beside `-o`'s file, or `.tmp_staging_stdout_<PID>/` inside the user's temp
directory for stdout-only runs. Simulate output also changed shape: with
neither `-o` nor `-O` set, stdout now prints the same content `-o` writes to
a file (run board plus every session's board and complete request), not the
run board alone - see the Quick Start section below.

**2026.9.9 is a breaking release for resource files.** The singular TOML key
`regex_pattern` is no longer accepted. A section that still sets it aborts
collection and names the section. Use `regex_patterns` as a list of strings:

```toml
regex_patterns = ['^##\s+', '^###\s+']
```

## Quick Start

Keep *resources* (what the model should know) separate from *prompts* (what you want it to do).

### 1. Extract the examples

```bash
dragiter-gen-examples .
cd examples/01_md_sample
```

### 2. Always simulate first

```bash
dragiter -s -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt
```

No network calls, no tokens spent. With neither `-o` nor `-O`, stdout prints
the aggregate run board (sessions, pack, window, routing) followed by every
session's board and complete outgoing request - the same content `-o` would
write to a file. Sections are joined with the configured `output_delimiter`;
within one section the board and the request stay separated by `***`. Add
`-O out` (or `-o file.md`) to write that content to files instead; stdout
then stays quiet. Shell redirection of stdout is not treated as a file sink.

### 3. Run against a local Ollama instance

```bash
dragiter -v -c config-ollama.toml -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt
```

`-v` writes the live run board on stderr, not onto the result sink. It is
advisable with local models; they can take their time and the silence is
otherwise rather disconcerting.

## Documentation

Documentation follows the Diátaxis framework and is deliberately split:

```bash
dragiter-gen-docs .
```

- `docs/manual.md` - Tutorial, How-to guides and Explanations
- `docs/reference.md` - Complete technical reference (flags, schemas, placeholders, defaults, activity log)
- `docs/info.txt` - Concise man-page summary (`dragiter --info`)
- `docs/faq.md` - Frequently asked questions and troubleshooting
- `docs/glossary.md` - Definitions of terms used across the documentation
- `docs/window-starting-values.md` - Starting values for `chars_per_token`, `max_context_tokens` and `max_output_tokens` per provider

## Configuration in brief

Settings are resolved in this strict order (highest priority first):

1. Command-line arguments
2. TOML configuration file (`-c`, `DRAGITER_CONFIG_FILE`, or `~/.config/dragiter/config.toml`)
3. Environment variables (`DRAGITER_*`)
4. Built-in defaults

A value set by a higher-priority source cannot be overridden by a lower one.

## Notable capabilities (all present in the code)

- Staged `regex_patterns`: pattern 0 always cuts; later patterns refine only pieces above `pack_limit_chars`
- Optional packing (`pack_limit_chars` on the section, or `--pack-limit-chars`) and a chunk cap (`--max-chunks`, default 200)
- Include/exclude filters and per-section `chunk_substitutions`
- Sequential or batched processing of material chunks
- Context-window estimation when `chars_per_token`, `max_context_tokens` and `max_output_tokens` are all set; otherwise boards show `n/a` / `--`
- JSONL loops that expose every object key as a template placeholder
- Stdin is read only when `-t` / `--task` is set or the prompt contains `{STDIN}`
- Activity tracing to JSONL for auditing
- Retry logic with configurable delay and maximum attempts (transient 5xx and connection drops; 504 / gateway timeout / runner crash are terminal)
- Optional mutual TLS (client certificate + key)
- Results on stdout only when neither `-o` nor `-O` is set; simulate output there matches `-o`'s shape exactly (run board plus every session's board and request); file routing replaces that sink
- `-o` and `-O` are mutually exclusive
- Output modes: exclusive create (`x`), overwrite (`w`), append (`a`)
- Verbose stderr run board; every run stages its completions in a hidden workspace until commit - `.tmp_staging_dir_<PID>/` inside `-O`'s directory, `.tmp_staging_file_<PID>/` beside `-o`'s file, or `.tmp_staging_stdout_<PID>/` inside the user's temp directory for stdout-only

## Tool Chaining (the Unix way)

Because dragiter does one job cleanly it composes with the rest of the terminal. Standard input is fully supported:

```bash
# Stdin into a prompt that contains {STDIN}; -o replaces the stdout sink
curl -s https://example-competitor.com/pricing \
  | dragiter -p summarize_pricing.toml -r web_resources.toml -o pricing_report.txt

# Omit -o/-O to echo the result (or the simulate board) on stdout
dragiter -s -p summarize_pricing.toml -r web_resources.toml > board.md
```

The same pattern works with database exports, log files or any other tool that can produce a stream.

## Acknowledgements

This project would still be an elegant collection of unfinished ideas without the tireless pair-programming assistance
of Grok and Gemini. Their code reviews and occasional refusal to let dubious design pass were invaluable.

Special thanks to Claude Code (Anthropic) for pair-programming, specification, testing and documentation work that
would otherwise have taken weeks.

Equal thanks are due to the broader Python community, whose libraries and documentation remain the foundation of tools
like this one.

Happy automating.
