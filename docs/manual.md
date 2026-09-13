# dragiter Manual

**dragiter** (Deterministic Context Iterator) is a focused command-line tool that integrates large language models into
automated workflows. It treats LLM processing as a Unix-style pipeline: material is read, chunked, combined with prompt
templates and optional iteration data, then sent to an OpenAI-compatible endpoint. Results are written according to
explicit routing rules.

This manual follows the Diátaxis framework. It contains:

- a **Tutorial** for first-time users,
- **How-to guides** for concrete tasks,
- **Explanations** of the underlying concepts.

Complete technical details — every configuration key, validation rule, exact TOML schemas, placeholder lists, defaults
and activity-log record formats — are documented in the separate **Technical Reference**. This manual deliberately
avoids duplicating that information.

British English is used throughout.

---

## Tutorial: Your first workflow

The quickest way to understand dragiter is to run the included examples.

### 1. Extract the examples

```bash
dragiter-gen-examples .
cd examples/01_md_sample
```

You now have a self-contained demonstration directory containing prompt templates, resource definitions, a loop file and
several ready-to-use configuration files.

### 2. Always start with simulation mode

Before spending API credits or waiting for a local model, verify that file routing and prompt assembly work correctly:

```bash
dragiter -s -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt
```

The `-s` flag prevents any network or model calls. When neither `-o` nor `-O` is
set, stdout prints the run board (sessions as request count, mode,
chunks, loops, effective pack budget and its origin, small/over, window). Each file under `-O` starts with a
session board (session index, file, chunk, section, valid, chars, tokens, pack, pack from, loop index), then a
blank line, then the role/content transcript of that query. A single `-o` file prints the run board once, then
one session board plus transcript per session. With `-o` or `-O`, the console
stays quiet.

### 3. Run against a local Ollama instance

If Ollama is installed and running with its default settings, use the provided configuration:

```bash
dragiter -v -c config-ollama.toml -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt
```

The `-v` (verbose) flag is recommended for local models. They can take considerably longer to respond than cloud
services; without it the terminal appears frozen. Verbose mode writes a short
board on stderr (start block, one request line per call with ◴◷◶◵ on the
left, closing block). It does not print onto stdout. Completions are also
copied into `.dragiter-partial/` as they finish.

### 4. Optional: make the configuration permanent

Copy a working configuration to the default location:

```bash
mkdir -p ~/.config/dragiter
cp config-ollama.toml ~/.config/dragiter/config.toml
```

Subsequent runs no longer need the `-c` flag:

```bash
dragiter -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt
```

Alternatively keep the configuration file inside the project and create a symbolic link:

```bash
ln -s $(pwd)/config-ollama.toml ~/.config/dragiter/config.toml
```

If you frequently switch between providers it is usually clearer to keep using the `-c` flag.

### 5. Use a cloud provider

Edit one of the cloud configuration files (for example `config-google.toml` or `config-grok.toml`).  
**Do not put a real API key into the file** — see “How to supply API keys securely” below.

Then run:

```bash
dragiter -v -c config-google.toml -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt
```

### 6. Configuration via environment variables

For CI pipelines or situations where credentials must not appear in files:

```bash
export DRAGITER_BASE_URL="http://localhost:11434/v1"
export DRAGITER_MODEL_NAME="qwen3:8b"
export DRAGITER_API_KEY="ollama"
dragiter -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt
```

Configuration sources are evaluated in a strict order of precedence (see the Explanation section and the Technical
Reference). Command-line arguments always win; environment variables only fill values that have not already been set by
a higher-priority source.

You have now completed the essential first workflow. The remaining sections show how to solve real tasks and explain the
design decisions behind the tool.

---

## How-to guides

### How to connect to different LLM services

dragiter speaks the OpenAI-compatible chat-completions protocol. Changing the underlying model therefore requires only
three settings: `base_url`, `model_name` and (when required) `api_key`.

**Local Ollama**

```bash
dragiter ... --base-url "http://localhost:11434/v1" \
             --model-name "llama3" \
             --api-key "dummy-key"
```

**xAI Grok**

```bash
dragiter ... --base-url "https://api.x.ai/v1" \
             --model-name "grok-4.3" \
             --api-key "YOUR_XAI_KEY"
```

**Google or other compatible providers**

Point `--base-url` at the provider’s OpenAI-compatible endpoint (or a proxy such as LiteLLM) and supply the appropriate
model name and key.

All three values may also be placed in a TOML configuration file or supplied as environment variables. Full details of
every configuration key appear in the Technical Reference.

### How to supply API keys securely

**Never put a real API key into a configuration file.**  
Configuration files are frequently committed to version control, copied, backed up or shared. Doing so is a serious
security risk.

dragiter reads the key from the environment variable `DRAGITER_API_KEY` (or from the `--api-key` command-line flag). Two
safe patterns are recommended.

#### A) Single provider (simplest)

Export the key once into the variable that dragiter expects, then call the tool normally.

**Linux / macOS / Git Bash / WSL**

```bash
export DRAGITER_API_KEY="xai-…"          # or your Claude / Gemini / OpenAI key
dragiter -v -c config-grok.toml -p prompt.toml -r resource.toml -l loop.txt
```

**Windows PowerShell**

```powershell
$env:DRAGITER_API_KEY = "xai-…"
dragiter -v -c config-grok.toml -p prompt.toml -r resource.toml -l loop.txt
```

**Windows cmd.exe**

```cmd
set DRAGITER_API_KEY=xai-…
dragiter -v -c config-grok.toml -p prompt.toml -r resource.toml -l loop.txt
```

#### B) Multiple providers

Keep provider-specific keys and map them only for the current invocation. The mapping exists solely for that one process
and disappears afterwards.

**Linux / macOS / Git Bash / WSL**

```bash
export GROK_API_KEY="xai-…"
export CLAUDE_API_KEY="sk-ant-…"
export GEMINI_API_KEY="AIza…"

# use Grok for this run
DRAGITER_API_KEY="$GROK_API_KEY" \
  dragiter -v -c config-grok.toml -p prompt.toml -r resource.toml -l loop.txt

# switch to Claude without changing any file
DRAGITER_API_KEY="$CLAUDE_API_KEY" \
  dragiter -v -c config-claude.toml -p prompt.toml -r resource.toml -l loop.txt
```

**Windows PowerShell**

```powershell
$env:GROK_API_KEY   = "xai-…"
$env:CLAUDE_API_KEY = "sk-ant-…"
$env:GEMINI_API_KEY = "AIza…"

# use Grok for this run
$env:DRAGITER_API_KEY = $env:GROK_API_KEY
dragiter -v -c config-grok.toml -p prompt.toml -r resource.toml -l loop.txt

# switch to Claude
$env:DRAGITER_API_KEY = $env:CLAUDE_API_KEY
dragiter -v -c config-claude.toml -p prompt.toml -r resource.toml -l loop.txt
```

**Windows cmd.exe**

```cmd
set GROK_API_KEY=xai-…
set CLAUDE_API_KEY=sk-ant-…
set GEMINI_API_KEY=AIza…

REM use Grok for this run
set DRAGITER_API_KEY=%GROK_API_KEY% && dragiter -v -c config-grok.toml -p prompt.toml -r resource.toml -l loop.txt

REM switch to Claude
set DRAGITER_API_KEY=%CLAUDE_API_KEY% && dragiter -v -c config-claude.toml -p prompt.toml -r resource.toml -l loop.txt
```

#### Additional notes

- Leave the `api_key = "…"` line in every `config-*.toml` **commented out**.
- Environment variables are ignored when the same key is already present in a loaded configuration file (see
  Configuration precedence). Therefore keep secrets out of the TOML files.
- The activity log automatically masks any field whose name contains the substring “key”.
- On Windows PowerShell the assignment `$env:VAR = …` persists for the remainder of the session; remove it afterwards
  with `Remove-Item Env:DRAGITER_API_KEY` if desired.

### How to define material (resources)

A resource file tells dragiter which documents to load and how to split them into manageable chunks.

Create a TOML file containing one or more named sections. Each section lists glob patterns and optional regular
expressions used for chunking:

```toml
[config01]
glob_patterns = ["docs/**/*.md"]
regex_patterns = ['^#+\s+.*$', '\n\n']
```

The first pattern always splits at match starts; the match text stays on the following piece. Capturing groups are
optional and ignored. Further patterns run only on pieces that still exceed `pack_limit_chars`. The singular key
`regex_pattern` is no longer accepted; a section that still sets it aborts collection and names the section.
Additional filters (`include_filters`, `exclude_filters`),
optional `chunk_substitutions` (literal search-and-replace on each piece after
the split), and a section-local `base_directory` are available; see the Technical
Reference for the complete schema.

```toml
chunk_substitutions = [
  { pattern = '[ \t]{2,}', replacement = " " },
  { pattern = '\n{3,}', replacement = "\n\n" },
]
```

Optional packing: after the staged regex split, consecutive chunks **from the same file** can be joined until a
character budget is reached. Set `pack_limit_chars` on the section, or globally via `--pack-limit-chars` /
`pack_limit_chars` / `DRAGITER_PACK_LIMIT_CHARS`. Unset or `0` disables packing and also disables overflow patterns
after the first. A globally set value, including `0`, overrides the section key. A single piece that no remaining
pattern can reduce stays intact. Valid and invalid chunks are not mixed.
A run that would produce more than 200 chunks aborts unless `--max-chunks` /
`max_chunks` / `DRAGITER_MAX_CHUNKS` raises the cap (minimum 1).

When you later run dragiter with `-r your_resource.toml`, the matched files are read, split according to the regex,
optionally rewritten by `chunk_substitutions`, and
become the material that can be injected into prompts via the `[MATERIAL]` placeholder and the `{CHUNK_*}` variables.

### How to write a prompt template

Prompt templates are also written in TOML and follow a fixed conceptual structure:

- `[system]` - the persona / system instruction
- `[task]` - the body of the prompt, normally subdivided into
    - `first` (introductory text),
    - `material` (how each chunk is formatted),
    - `synthesis` (the actual question or instruction given to the model)
- `[behaviour]` - temperature and sequential-processing flags
- `[outcome]` - output-filename schema and delimiter

Inside the `material` and `synthesis` strings you may use the reserved placeholders `{CHUNK_CONTENT}`,
`{CHUNK_FILE_NAME}`, `{LOOP_CONTENT}` and others. A complete list of recognised placeholders is given in the Technical
Reference.

A minimal working skeleton looks like this:

```toml
[system]
instruction = """
You are a precise technical analyst.
Answer in British English and use Markdown tables.
"""

[task]
first = """
### REFERENCE MATERIAL
"""

material = """
FILE: {CHUNK_FILE_NAME}
CONTENT:
{CHUNK_CONTENT}
"""

synthesis = """
Using the material above, answer the following question:

{LOOP_CONTENT}
"""

[behaviour]
temperature = 0.0

[outcome]
output_filename_schema = "result.txt"
```

### How to iterate over many items (loop files)

Two formats are supported.

**Plain text** - one task per line. Each non-empty line becomes the value of `{LOOP_CONTENT}`.

**JSON Lines** - one JSON object per line. Every key of the object is available as a placeholder (for example
`{language}`, `{region}`, `{tone}`).

Example JSONL:

```json
{
  "language": "German",
  "region": "DACH",
  "tone": "formal"
}
{
  "language": "Spanish",
  "region": "Latin America",
  "tone": "enthusiastic"
}
```

Place the corresponding placeholders inside the `synthesis` block of your prompt template. dragiter executes the entire
prompt once for each line.

### How to control where results are written

- `-o FILE` writes everything to a single file.
- `-O DIRECTORY` writes one file per result into the given directory (recommended for batch work).
- `-m x|w|a` selects exclusive-create, overwrite or append behaviour.
- An `output_filename_schema` (defined in the prompt’s `[outcome]` section or via configuration) may contain chunk- and
  loop-related placeholders so that each result receives a meaningful name.

When multiple results land in the same file, the value of `output_delimiter` is inserted between them.

### How to keep requests inside the model’s context window

Three related settings govern token estimation:

- `chars_per_token` - average characters per token (commonly 4.0 for European languages),
- `max_context_tokens` - the model’s total context window (input + output),
- `max_output_tokens` - the portion reserved for the model’s reply.

Once these values are set, dragiter estimates the size of every assembled prompt and refuses to send requests that would
exceed the limit. This protects both reliability and cost.

Recommended starting points appear in the Technical Reference and in the example configuration files. For local models
with smaller windows begin with a conservative `max_context_tokens`; for modern cloud models 128 000 is a typical safe
value.

### How to build larger automation pipelines

Because dragiter follows the Unix philosophy it composes cleanly with ordinary shell tools.

**Fetch live web data and summarise it**

```bash
#!/bin/bash
curl -s https://example-competitor.com/pricing > /tmp/current_pricing.html
dragiter -p summarize_pricing.toml -r web_resources.toml -o pricing_report.txt
```

**Export database rows and analyse sentiment**

```bash
#!/bin/bash
psql -U admin -d support_db -c \
  "COPY (SELECT review_text FROM tickets WHERE date = CURRENT_DATE - 1) TO STDOUT WITH CSV;" \
  > /tmp/daily_reviews.csv
dragiter -p sentiment_prompt.toml -r review_resources.toml -o daily_sentiment.md
```

The same pattern works with any tool that can produce a file: version-control checkouts, log aggregators, document
converters, etc.

### How to run a security audit over a legacy codebase

Configure a resource file that selects `*.c` / `*.h` files and splits them at function boundaries. Write a prompt that
casts the model as a senior security auditor and asks for buffer-overflow and memory-management findings formatted as a
Markdown table. Then:

```bash
dragiter -p audit_prompt.toml -r legacy_code_resource.toml -O ./audit_results
```

Each function-level analysis lands in its own file inside `audit_results`.

### How to extract metrics from a collection of quarterly reports

Prepare a loop file containing the metric names of interest (“Operating Costs”, “Net Profit”, \ldots). Point the
resource file at the report directory and chunk by major section headers. Use `{LOOP_CONTENT}` inside the synthesis
block. Finally:

```bash
dragiter -p extract_prompt.toml -r quarterly_reports.toml -l metrics_loop.txt \
         -o final_summary.txt -m a
```

All answers are appended to a single readable summary file.

### How to generate localised marketing copy from a master manual

Create a JSONL loop file whose objects contain `language`, `region` and `tone`. Write a prompt that inserts those three
placeholders into the synthesis instruction. Run:

```bash
dragiter -p localized_prompt.toml -r master_manual.toml -l target_markets.jsonl \
         -O ./campaigns
```

One tailored document appears for each market.

---

## Explanation

### Design philosophy

dragiter is intentionally narrow. It does not try to be a full agent framework, a prompt IDE or a model-serving
platform. Its single responsibility is to turn a deterministic combination of material, template and iteration data into
one or more well-formed LLM requests and to route the answers according to explicit rules.

This design yields three practical benefits:

1. **Reproducibility** - the same inputs always produce the same request payloads (temperature 0.0 is the recommended
   default).
2. **Composability** - the tool slots into ordinary shell pipelines and CI jobs.
3. **Provider independence** - any OpenAI-compatible endpoint can be used simply by changing three configuration values.

Live completions always stream. That keeps the HTTP read side open for long-thinking local models; combine it with
`-v` (logger heartbeat every ten seconds) and `--tcp-keep-alive` when a run lasts more than a few seconds.

Transient HTTP 500/502/503 responses and connection drops are retried when
`max_retry` is set. HTTP 504, gateway/stream timeouts and an Ollama runner
crash are not: repeating the same heavy prompt will not recover them.
`max_retry` counts **attempts** (unset means one try). `retry_delay` is the
base wait before a later attempt and doubles each time; unset means 3 seconds.
The OpenAI SDK does not retry on its own. Exact classification lives in the
Technical Reference.

### Configuration precedence

Settings are resolved once, in a fixed order:

1. Command-line arguments
2. TOML configuration file (explicit `-c`, `DRAGITER_CONFIG_FILE`, or `~/.config/dragiter/config.toml`)
3. Environment variables (`DRAGITER_*`)
4. Built-in defaults

A value set by a higher-priority source can never be overwritten by a lower-priority source. Consequently an environment
variable cannot override a key that is already present in a configuration file. Environment variables are therefore most
useful when no configuration file is loaded at all, or when you wish to inject secrets without writing them to disk.

Full lists of recognised keys and their types appear in the Technical Reference.

### Material, chunks and the context window

Large documents are rarely useful when sent as a single undifferentiated block. dragiter therefore encourages (and helps
you enforce) a deliberate chunking strategy. The resource file’s regular expressions determine the logical units;
`pack_limit_chars` can then pack several of those units from one file into a larger piece. The prompt template decides
how those units are presented to the model.

Token estimation is deliberately simple and conservative: character count divided by `chars_per_token`. The resulting
estimate is compared against the remaining context budget (`max_context_tokens` − `max_output_tokens`). Requests that
would exceed the budget are rejected before any network call is made. This behaviour is intentional: it is better to
fail early and loudly than to discover mid-batch that half the work was truncated by the provider.

### Hard safety limits (circuit breakers)

In addition to the configurable context-window checks, dragiter enforces three hard, non-configurable limits:

- **100 MB** - maximum size of any single input file
- **200 chunks** - maximum number of material chunks that may be produced from all resources combined
- **50 loop items** - maximum number of entries in a loop file

These circuit breakers prevent accidental combinatorial explosion and protect both memory and API budgets. When a limit
is exceeded the process aborts with a clear error message. The usual remedy is to split the work into smaller batches.

Soft warnings are also issued when individual chunks fall outside a sensible size range (fewer than 50 or more than 20
000 characters); the run continues, but the warnings should prompt a review of the chunking regular expression.

Full details appear in the Technical Reference.

### Sequential versus batched processing

By default all chunks belonging to a single iteration are assembled into one request. The `sequential_processing` flag
(or the corresponding configuration key) forces each chunk to be processed in its own request. Sequential mode is useful
when individual chunks are already large, when you need per-chunk output files, or when you want to stay well below a
provider’s rate limits.

### Activity logging

When an activity file is requested (`-a` / `DRAGITER_ACTIVITY_FILE`) dragiter appends a structured JSON Lines record for
every major stage of the pipeline: configuration snapshot, discovered resources, material statistics, loop items,
assembled sessions, token counts and final results. Sensitive fields whose names contain the substring “key” are masked.
The resulting file is suitable for auditing and for post-mortem analysis of long-running batch jobs. The exact record
formats are described in the Technical Reference.

---

## Running the test suite

The test suite is not shipped inside the installed wheel. Obtain the source distribution, install the development extras
and run pytest:

```bash
pip download dragiter --no-binary=:all: -d .
tar xf dragiter-*.tar.gz
cd dragiter-*/
pip install -e ".[dev]"
pytest -q
```

Most tests execute without any network access or API keys. Optional integration tests that require a local Ollama
instance are automatically skipped when the service is unavailable.

---

## Acknowledgements

The development of dragiter benefited greatly from the pair-programming assistance of the Grok and Gemini models and
from the broader Python open-source ecosystem. Their documentation, libraries and community norms remain the foundation
on which tools of this kind are built.

Happy automating.
