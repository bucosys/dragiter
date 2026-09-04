# dragiter Technical Reference

**Version:** derived from source (2026.9.1)  
**Language:** British English  
**Scope:** Configuration, file formats, CLI, defaults, output behaviour and activity log  
**Sources:** Source code (`src/dragiter/`), in particular `PromptCreator`, `OpenAIServiceExt` and example TOML files under `examples/`

This document is the technical reference. It describes what the program actually accepts and does. It does **not**
replace the user manual or how-to guides.

---

## 1. Configuration precedence

dragiter resolves every setting in the following order (highest priority first):

1. Command-line arguments
2. TOML configuration file (`-c` / `DRAGITER_CONFIG_FILE` / `~/.config/dragiter/config.toml`)
3. Environment variables (`DRAGITER_*`)
4. Built-in defaults (applied only when a value is still unset)

Once a value has been set by a higher-priority source it cannot be overwritten by a lower-priority source.

### Special case: prompt-related settings

Four settings that can also appear inside a prompt template file are handled by the `PromptCreator`:

- `temperature`
- `sequential_processing`
- `output_delimiter`
- `output_filename_schema`

When a prompt file (`-p`) is supplied, the effective precedence for these four settings becomes:

1. Command-line arguments
2. Main configuration system (TOML config file or environment variables)
3. Values present in the prompt template itself (`[behaviour]` / `[outcome]` sections)
4. Hard-coded defaults inside `PromptCreator`  
   (`temperature = 0.0`, `sequential_processing = false`,  
   `output_delimiter = "\n"`, `output_filename_schema = "dragiter-out.txt"`)

In other words, the prompt template acts as an additional, lower-priority layer that is consulted only when the setting
has not already been supplied by the CLI or the main configuration system.

### Config file discovery order

When no `--config-file` / `-c` is given:

1. Environment variable `DRAGITER_CONFIG_FILE`
2. Default location `~/.config/dragiter/config.toml` (only if the file exists)

When both `-b` / `--base-directory` and `-c` / `--config-file` are set, a **relative**
`-c` path is rebased onto `-b` **before** the file is read. Absolute `-c` paths are
left unchanged. `config_file` is not part of the later general path-rebase pass.

---

## 1a. LLM client and runtime requirements

The CLI wires `OpenAIServiceExt` (`src/dragiter/infrastructure/llm/openai_service_ext.py`).

- Live completions **always stream** (`stream=True`).
- The HTTP stack is **httpx2** via `openai.DefaultHttpx2Client`.
- Read timeout is unlimited; connect / write / pool timeouts stay bounded.
- `--tcp-keep-alive` maps to `httpx2.HTTPTransport(socket_options=...)`.
- Hard install floor: `openai>=3.0.0` and `httpx2>=2.7.0`. openai 1.x / 2.x do
  **not** export `DefaultHttpx2Client` and do not install `httpx2`.
- The non-streaming `OpenAIService` remains in the tree and still uses classic
  `httpx`; it is not the CLI default.

With `-v` / `--verbose` the adapter emits an INFO heartbeat on the logger
every ten seconds while a streamed completion is still running. It does
**not** write a spinner to stdout (that would corrupt result files).
Payload dumps stay on DEBUG.

The OpenAI SDK’s own retries are disabled (`max_retries=0`). The adapter
owns the retry loop via `CompletionRetryPolicy`
(`src/dragiter/infrastructure/llm/openai_runtime.py`).

### Retries

`max_retry` is the **number of completion attempts**, not the number of
extra tries after a failure.

| Setting        | When unset                         | When set                         |
|----------------|------------------------------------|----------------------------------|
| `max_retry`    | one attempt                        | `max(1, value)` attempts         |
| `retry_delay`  | 3 seconds between later attempts   | that many seconds as the base    |

Backoff before attempt *n* (1-based): no wait on attempt 1; then
`retry_delay`, `2 × retry_delay`, `4 × retry_delay`, …

**Retried** (until `max_retry` is exhausted):

- HTTP 429 (`RateLimitError`)
- transport / connection failures (`APIConnectionError`)
- transient HTTP 5xx from a proxy or backend (500, 502, 503, and any
  other 5xx that is not a gateway timeout)

**Not retried** (the attempt fails immediately):

- HTTP 504, and responses whose message contains `gateway timeout` or
  `stream timeout`
- `APITimeoutError`
- an Ollama runner crash (`model runner has unexpectedly stopped`)
- client 4xx other than 429

Transport and SDK construction failures are reported as
“Failed to initialise OpenAI client …”. Failures after the client exists
are reported as “Attempt *n*/*m* failed: …”. They are **not** labelled as
certificate or CA-bundle problems.

---

## 2. Configuration settings (complete list)

All settings that appear in the configuration loader are listed below.

| Key (TOML / long CLI)    | Short CLI | Type   | Default (when unset)      | Description                                                    |
|--------------------------|-----------|--------|---------------------------|----------------------------------------------------------------|
| `debug`                  | `-d`      | bool   | `false`                   | Enable debug logging                                           |
| `simulate`               | `-s`      | bool   | `false`                   | Simulation mode (no API calls)                                 |
| `verbose`                | `-v`      | bool   | `false`                   | Verbose output                                                 |
| `sequential_processing`  | —         | bool   | `false`                   | `--sequential-processing`: one request per chunk               |
| `tcp_keep_alive`         | —         | bool   | `false`                   | `--tcp-keep-alive` on the httpx2 transport                     |
| `api_key`                | —         | string | (none)                    | API key for the LLM service                                    |
| `base_url`               | —         | string | (none)                    | Base URL of the OpenAI-compatible endpoint                     |
| `model_name`             | —         | string | (none)                    | Model identifier                                               |
| `output_delimiter`       | —         | string | (none)                    | Delimiter written between multiple results                     |
| `output_filename_schema` | —         | string | (none)                    | Filename template for output files                             |
| `output_mode`            | `-m`      | string | `"x"`                     | File open mode: `x` (exclusive), `w` (overwrite), `a` (append) |
| `task`                   | `-t`      | string | (none)                    | Direct task text (alternative to a prompt file)                |
| `max_context_tokens`     | —         | int    | (none)                    | Maximum total tokens the model can handle                      |
| `max_output_tokens`      | —         | int    | (none)                    | Maximum tokens the model may generate                          |
| `chars_per_token`        | —         | float  | (none)*                   | Average characters per token used for estimation               |
| `temperature`            | —         | float  | (none)                    | Sampling temperature                                           |
| `retry_delay`            | —         | int    | 3 s at runtime if unset   | Base wait between attempts 2…*n*; doubles each time            |
| `max_retry`              | —         | int    | 1 attempt if unset        | Maximum number of completion attempts (not extra retries)      |
| `pack_limit_chars`        | —         | int    | (none) / off              | Pack consecutive regex chunks per file up to N characters      |
| `base_directory`         | `-b`      | path   | (unset)                   | Base for relative paths. **Not** pre-filled with CWD           |
| `activity_file`          | `-a`      | path   | (none)                    | Write activity log to this file                                |
| `ca_bundle_file`         | —         | path   | (none)                    | Custom CA certificate bundle (PEM)                             |
| `client_cert_file`       | —         | path   | (none)                    | Client certificate for mTLS                                    |
| `client_key_file`        | —         | path   | (none)                    | Client private key for mTLS                                    |
| `config_file`            | `-c`      | path   | (see discovery)           | Path to TOML configuration file                                |
| `log_file`               | `-L`      | path   | (none)                    | Write log output to file (append, no rotation)                 |
| `prompt_file`            | `-p`      | path   | (none)                    | Path to prompt template (`.toml`)                              |
| `loop_file`              | `-l`      | path   | (none)                    | Path to loop file (`.txt` or `.jsonl`)                         |
| `resource_file`          | `-r`      | path   | (none)                    | Path to resource definition (`.toml`)                          |
| `output_file`            | `-o`      | path   | (none)                    | Write all output to a single file                              |
| `output_directory`       | `-O`      | path   | (none)                    | Write outputs into this directory                              |

\* The example configuration files document `chars_per_token = 4.0` as the conventional default used for estimation when
the setting is left unset.

### Mandatory settings (when not in simulation mode)

- `base_url` must be set (CLI, config file or environment).
- Either a `prompt_file` (`-p`) **or** a direct `task` (`-t`) must be supplied.
- When a loop is used, a `resource_file` is normally required as well.

### Validation rules (from the validator)

- `output_mode` must be one of `a`, `w`, `x`.
- `retry_delay` (when set) must be between 0 and 20 inclusive.
- `max_retry` (when set) must be between 0 and 9 inclusive. The adapter
  still performs at least one attempt (`max(1, value)`), so `0` and
  “unset” both mean a single try.
- `chars_per_token` (when set) must be greater than 0.0.
- `pack_limit_chars` (when set) must be ≥ 0. `0` disables packing.
- Paths that are required must be readable (or writable for output paths).
- `client_key_file` without `client_cert_file` is rejected.
- `base_url` is optional in simulation mode.

### Hard limits (circuit breakers)

These limits are enforced at runtime and **cannot be configured**. They exist to protect against accidental
combinatorial explosion, excessive memory consumption and runaway API costs.

| Limit                | Value  | Component              | Behaviour on breach                     |
|----------------------|--------|------------------------|-----------------------------------------|
| Maximum file size    | 100 MB | `SimpleTextFileReader` | Raises `TextFileReaderError` and aborts |
| Maximum total chunks | 200    | `MaterialTokenizer`    | Raises an error and aborts processing   |
| Maximum loop items   | 50     | `LoopBuilder`          | Raises `LoopBuilderError` and aborts    |

In addition the `MaterialTokenizer` emits warnings (but continues) when an individual chunk is unusually small (< 50
characters) or unusually large (> 20 000 characters). These warnings help detect poorly chosen regular expressions.

The limits are intentional design decisions. When a limit is hit the recommended action is to split the input (smaller
files, fewer loop entries, or a tighter chunking regex) and run dragiter multiple times.

---

## 3. Environment variables

Every configuration key can be supplied as an environment variable by prefixing it with `DRAGITER_` and converting it to
upper case:

```
DRAGITER_API_KEY
DRAGITER_BASE_URL
DRAGITER_MODEL_NAME
DRAGITER_MAX_CONTEXT_TOKENS
DRAGITER_MAX_OUTPUT_TOKENS
DRAGITER_CHARS_PER_TOKEN
DRAGITER_TEMPERATURE
DRAGITER_RETRY_DELAY
DRAGITER_MAX_RETRY
DRAGITER_PACK_LIMIT_CHARS
DRAGITER_BASE_DIRECTORY
DRAGITER_CONFIG_FILE
DRAGITER_PROMPT_FILE
DRAGITER_RESOURCE_FILE
DRAGITER_LOOP_FILE
DRAGITER_OUTPUT_FILE
DRAGITER_OUTPUT_DIRECTORY
DRAGITER_OUTPUT_MODE
DRAGITER_ACTIVITY_FILE
DRAGITER_LOG_FILE
DRAGITER_TCP_KEEP_ALIVE
DRAGITER_SEQUENTIAL_PROCESSING
DRAGITER_OUTPUT_FILENAME_SCHEMA
DRAGITER_OUTPUT_DELIMITER
...
```

Boolean environment values consumed by `ConfigurationLoader` are parsed by
`BoolSetting.from_string` after strip and case-fold:

- truthy: `TRUE`, `1`, `YES`, `ON`, `Y`
- falsy: `FALSE`, `0`, `NO`, `OFF`, `N`
- anything else (including the empty string) raises

Early logging (`LoggingConfigurator`, before the loader runs) only treats
`TRUE`, `1` and `YES` as truthy for `--debug` / `--verbose` equivalents.
It also builds those environment names from raw `sys.argv[0]`, so
`DRAGITER_DEBUG` / `DRAGITER_VERBOSE` / `DRAGITER_LOG_FILE` are reliable
when the process name is exactly `dragiter`. Prefer the CLI flags
`-d`, `-v` and `-L` if the executable path is absolute.

The TOML config-file path does **not** run that parser. It assigns the native TOML
type. Use `simulate = true` / `false`, not `"true"`. Quoted boolean strings in a
config file are rejected.

Environment variables are applied **after** the configuration file and only fill values that are still unset. Values that start with `$` are expanded via `os.path.expandvars` before type conversion.

---

## 4. Main configuration file (TOML)

Example taken from `examples/01_md_sample/config-ollama.toml`:

```toml
api_key = "Ollama"
base_url = "http://localhost:11434/v1"
model_name = "qwen3:8b"
tcp_keep_alive = true

# Optional advanced settings
# chars_per_token = 3.8
# max_context_tokens = 32000
# max_output_tokens = 4000
# retry_delay = 5
# max_retry = 3
# pack_limit_chars = 4000
```

The same keys appear in `config-google.toml` and `config-grok.toml` with different endpoint values.

All keys are flat (no nested tables are required for the main configuration).

---

## 5. Prompt file format (TOML)

Observed structure from `examples/01_md_sample/01_prompt_md.toml` and the `PromptTemplate` domain model:

```toml
[system]
instruction = """
You are a precise analyst.
Always answer in English and use Markdown tables.
"""

[task]
first = """
### REFERENCE MATERIAL
Use the following material as a knowledge base:
"""

material = """
ID: {CHUNK_NUM_ID:04d}
FILE: {CHUNK_FILE_NAME}
SECTION: {CHUNK_SECTION_NAME}
SECTION NUM ID: {CHUNK_SECTION_NUM_ID}
CONTENT:

{CHUNK_CONTENT}
"""

synthesis = """
As a precise analyst, evaluate the provided historical reference material
to answer the following core question:

**"{LOOP_CONTENT}"**

Extract the key arguments from the text and present your findings
strictly as a Markdown table with the columns:
"Historical Concept", "Core Argument", and "Meaning for Modern AI".
"""

[behaviour]
temperature = 0.0
sequential_processing = false

[outcome]
output_delimiter = "\n---\n"
output_filename_schema = "sample_01.txt"
```

### Placeholders recognised in templates

- `{CHUNK_NUM_ID}` / `{CHUNK_NUM_ID:04d}`
- `{CHUNK_FILE_NAME}`
- `{CHUNK_SECTION_NAME}`
- `{CHUNK_SECTION_NUM_ID}`
- `{CHUNK_CONTENT}`
- `{LOOP_CONTENT}`
- `{LOOP_NUM_ID}` (and other keys that may appear in a loop dictionary)
- `{STDIN}` (replaced by content read from standard input, if any)

### Defaults applied by PromptCreator

The example values shown in the sample `prompt.toml` above are **not** the code defaults.  
They are merely the values chosen for that particular demonstration file.

When a prompt file is loaded, the `PromptCreator` applies the following **hard-coded defaults** for any key that is
missing from both the main configuration system and the prompt template itself:

| Key                      | Hard-coded default   |
|--------------------------|----------------------|
| `temperature`            | `0.0`                |
| `sequential_processing`  | `false`              |
| `output_delimiter`       | `"\n"`               |
| `output_filename_schema` | `"dragiter-out.txt"` |

These form the lowest priority layer (see section 1).  
Consequently a prompt template that omits `[behaviour]` or `[outcome]` entirely still receives a fully populated
`PromptTemplate` object.

The `PromptTemplate` object stores:

- `instruction`
- `first`
- `material`
- `synthesis`
- `temperature`
- `sequential_processing`
- `output_filename_schema`
- `output_delimiter`

---

## 6. Resource file format (TOML)

Observed structure from `examples/01_md_sample/01_resource_md.toml`:

```toml
[config01]
glob_patterns = ["**/*_engine.md", "**/*_thought.md"]
regex_pattern = '(^#+\s+.*$)'

[config02]
glob_patterns = ["**/*_automata.txt"]
regex_pattern = '(^\d+\.\s+.*$)'
```

Each table name becomes a **section name**.  
Inside a section the following keys are used:

- `glob_patterns` - list of glob patterns relative to the section search root
- `base_directory` (optional, per section) - search root for those globs. If omitted,
  the collector starts from `Path.cwd()`. When `-b` is set, that root is rebased onto
  `-b` **only if the original value was relative**. An absolute section
  `base_directory` is not moved by `-b`. The global `BaseDirectoryPathSetting` itself
  is never pre-filled with CWD.
- `regex_pattern` - regular expression used to split the matched files into chunks (default when omitted: a pattern that
  matches nothing)
- Optional filters (supported by the `ResourceSection` model): `exclude_filters`, `include_filters`
- `pack_limit_chars` (optional, per section) - after the regex split, join consecutive chunks of the **same file**
  until this many characters would be exceeded. Measured in characters. `0` or omitted means no packing. A globally set
  `pack_limit_chars` (CLI `--pack-limit-chars`, config file or `DRAGITER_PACK_LIMIT_CHARS`) overrides the section value,
  including when the global value is `0`. Packing never splits a chunk and never crosses a file or section boundary.
  Only runs of chunks that share the same `valid` flag are joined.

Resolved matches that escape the section root (including symlinks that point outside)
are skipped.

Multiple sections may be defined; they are processed independently.

---

## 7. Loop file formats

### Plain text (`.txt`)

One task per line. Example from `01_loop_md.txt`:

```
What exactly separates genuine human reasoning from mere mechanical calculation?
What fundamental limitations of artificial machines are identified here?
How is the relationship between symbols, language, and true intelligence described?
```

Each non-empty line becomes a loop item with the key `LOOP_CONTENT`.

### JSON Lines (`.jsonl`)

Supported by the loop builder (one JSON object per line).  
Any keys present in the objects are available as placeholders in the prompt templates.

---

## 8. CLI reference (main flags)

```
dragiter [options]

  -d, --debug
  -s, --simulate
  -v, --verbose
  -c, --config-file PATH
  -p, --prompt-file PATH
  -r, --resource-file PATH
  -l, --loop-file PATH
  -o, --output-file PATH
  -O, --output-directory PATH
  -b, --base-directory PATH
  -a, --activity-file PATH
  -L, --log-file PATH
  -m, --output-mode {x|w|a}
  -t, --task TEXT
  --api-key TEXT
  --base-url URL
  --model-name NAME
  --max-context-tokens INT
  --max-output-tokens INT
  --chars-per-token FLOAT
  --temperature FLOAT
  --retry-delay INT
  --max-retry INT
  --ca-bundle-file PATH
  --client-cert-file PATH
  --client-key-file PATH
  --tcp-keep-alive
  --sequential-processing
  --output-delimiter TEXT
  --output-filename-schema TEXT
  --info
  --version
```

Additional entry points:

- `dragiter-gen-examples` - extract the example trees
- `dragiter-gen-docs` - extract the documentation

---

## 9. Output behaviour

### Filename generation

When an `output_filename_schema` is supplied, the following placeholders are substituted (see
`OutputWriter._format_filename`):

- Chunk-related: `CHUNK_NUM_ID`, `CHUNK_FILE_NAME`, `CHUNK_SECTION_NAME`, `CHUNK_SECTION_NUM_ID`
- Loop-related: any key present in the current loop dictionary (especially `LOOP_NUM_ID`, `LOOP_CONTENT`)
- A high-resolution sortable timestamp can be generated internally (`YYYYMMDD_HHMMSS_nnnnnnnnn`)

Filenames are sanitised before being written.

### File open modes

Controlled by `output_mode`:

| Value | Behaviour                                                     |
|-------|---------------------------------------------------------------|
| `x`   | Exclusive create (default). Fails if the file already exists. |
| `w`   | Overwrite                                                     |
| `a`   | Append                                                        |

### Delimiter

When multiple results are written to the same file, the value of `output_delimiter` is inserted between them.

---

## 10. Activity log format

When the setting `activity_file` (CLI `-a` / environment `DRAGITER_ACTIVITY_FILE`) is set, dragiter writes a detailed
activity trace.

### 10.1 File format

The activity file is a **JSON Lines** (JSONL) file.

- Encoding: UTF-8
- One JSON object per line
- Lines are appended; the file is never truncated by the logger
- Serialisation uses `json.dumps(..., ensure_ascii=False, default=str)`

Every record is enhanced with two envelope fields:

| Field | Type     | Description                                                                                |
|-------|----------|--------------------------------------------------------------------------------------------|
| `TS`  | datetime | Timestamp of the event in UTC                                                              |
| `RT`  | string   | Runtime type - the class name of the object that produced the record (or a special marker) |

### 10.2 Lifecycle records

**Process start** (first record):

```json
{
  "TS": "2026-08-11T19:00:00.123456+00:00",
  "RT": "ActivityLogger",
  "initial_status_message": "dragiter(2026.7.26) process started"
}
```

**Process finish** (produced by `ApplicationResult`):

```json
{
  "TS": "...",
  "RT": "ApplicationResult",
  "final_status_message": "dragiter(2026.7.26) process finished with SUCCESS"
}
```

or with `FAILURE`.

**Exception record:**

```json
{
  "TS": "...",
  "RT": "Exception",
  "type": "ConfigurationValidatorError",
  "message": "...",
  "module": "dragiter.application.config.configuration_validator",
  "traceback": "Traceback (most recent call last):\n  ...",
  "location": 42,
  "filename": "/path/to/file.py",
  "lineno": 42
}
```

### 10.3 Domain activity records

Whenever an object that implements the `ActivityProvider` protocol is stored, its `to_activity_dict_list()` method is
called and the returned dictionaries are written (each with the `TS` / `RT` envelope).

#### Value-settings based records

Classes inheriting from `ValueSettingsActivityProvider` (`AIServiceParameters`, `ProcessingParameters`, path/output
parameter objects, …).

Keys that contain the substring `"key"` have their value replaced by `***MASKED***`.

Example:

```json
{
  "TS": "...",
  "RT": "AIServiceParameters",
  "api_key": "***MASKED***",
  "base_url": "http://localhost:11434/v1",
  "model_name": "qwen3:8b",
  "max_context_tokens": 32000,
  "max_output_tokens": 4000,
  "chars_per_token": 4.0,
  "temperature": 0.0,
  "retry_delay": 5,
  "max_retry": 3
}
```

#### Resources

```json
{
  "TS": "...",
  "RT": "Resources",
  "resource_sections_count": 2,
  "total_files": 3,
  "sections": [
    {
      "section_name": "config01",
      "file_count": 2,
      "regex_pattern": "(^#+\\s+.*$)",
      "exclude_filters": [],
      "include_filters": [],
      "pack_limit_chars": 4000,
      "files": 2}
    }
  ]
}
```

#### Material (chunks)

First a global summary, then one record per source file:

```json
{
  "TS": "...",
  "RT": "Material",
  "material_chunks_count": 12,
  "total_characters": 45821,
  "unique_sources": 3,
  "average_chunk_size": 3818.4,
  "max_chunk_size": 9200,
  "min_chunk_size": 412
}
```

```json
{
  "TS": "...",
  "RT": "Material",
  "file_num": 1,
  "file": "lovelace_1843_analytical_engine.md",
  "num_chunks": 5,
  "min_chunk_size": 412,
  "max_chunk_size": 2100,
  "avg_chunk_size": 1180.4
}
```

#### Loop

```json
{
  "TS": "...",
  "RT": "Loop",
  "loop_items_count": 3,
  "has_json_structure": false,
  "average_keys_per_item": 1.0,
  "total_keys_across_all_items": 3
}
```

#### PromptTemplate

```json
{
  "TS": "...",
  "RT": "PromptTemplate",
  "instruction_length": 78,
  "first_length": 64,
  "material_template_length": 142,
  "synthesis_length": 312,
  "temperature": 0.0,
  "sequential_processing": false,
  "output_filename_schema": "sample_01.txt",
  "output_delimiter": "\n---\n",
  "total_template_length": 596
}
```

#### ChatSessions

Aggregated summary, then (when verbose) one record per input message:

```json
{
  "TS": "...",
  "RT": "ChatSessions",
  "chat_sessions_count": 3,
  "total_input_messages": 9,
  "sessions_with_chunk": 3,
  "sessions_with_loop_item": 3
}
```

#### ChatResults

Aggregated summary, then one detailed record per result:

```json
{
  "TS": "...",
  "RT": "ChatResults",
  "chat_results_count": 3,
  "total_input_tokens": 12450,
  "total_output_tokens": 1890,
  "total_duration_ms": 14230,
  "has_results": true
}
```

```json
{
  "TS": "...",
  "RT": "ChatResults",
  "result_index": 1,
  "output_chars": 612,
  "input_tokens": 4150,
  "output_tokens": 630,
  "duration_ms": 4780,
  "finish_reason": "stop",
  "role": "assistant",
  "content": "| Historical Concept | Core Argument | Meaning for Modern AI |\n| ... |"
}
```

### 10.4 Order of records

A typical successful run produces records roughly in this order:

1. Process-start record
2. Configuration / settings records (`AIServiceParameters`, `ProcessingParameters`, path parameters, …)
3. `Resources`
4. `Material` (global summary + per-file records)
5. `Loop`
6. `PromptTemplate`
7. `ChatSessions` (summary + optional detail lines)
8. `ChatResults` (summary + one line per result)
9. Process-finish record (`ApplicationResult`)

Exact presence and cardinality depend on the pipeline path taken (simulation mode, presence of a loop file, etc.).

### 10.5 Implementation notes

- The concrete logger is `FileActivityLogger`, which inherits from `BufferedActivityLogger`.
- Records are kept in an in-memory list and flushed to disk on every `write_activity` / `write_exception` call.
- Sensitive values are masked only when the setting key contains the substring `"key"` (case-sensitive). Consequently
  `api_key` is masked; other fields are written in clear text.

---

## 11. Built-in defaults summary

### Main configuration system

| Setting                                                                 | Applied default                                                |
|-------------------------------------------------------------------------|----------------------------------------------------------------|
| `base_directory`                                                        | Unset. Not pre-filled with `Path.cwd()`                        |
| `output_mode`                                                           | `"x"` (factory default in `ConfigurationLoader`)               |
| Boolean flags (`debug`, `simulate`, `verbose`, `sequential_processing`, `tcp_keep_alive`) | Unset until supplied; treated as false when read as `.value` on an unset flag |
| All other settings                                                      | Remain unset until supplied by CLI, config file or environment |

Token-related values (`chars_per_token`, `max_context_tokens`, `max_output_tokens`) have no hard-coded numeric default
inside the validator; the example configuration files document the conventional values used for estimation
(`chars_per_token = 4.0`).

### PromptCreator hard-coded defaults

These defaults are applied by the `PromptCreator` when a prompt file is loaded and the corresponding key has not been
supplied by a higher-priority source (CLI, main config, environment, or the prompt template itself). See also section 1
and section 5.

| Setting                  | Hard-coded default   |
|--------------------------|----------------------|
| `temperature`            | `0.0`                |
| `sequential_processing`  | `false`              |
| `output_delimiter`       | `"\n"`               |
| `output_filename_schema` | `"dragiter-out.txt"` |

---

## 12. Related source locations

**Configuration**

- Configuration loading: `src/dragiter/application/config/configuration_loader.py`
- Validation & defaults: `src/dragiter/application/config/configuration_validator.py`
- Settings classes: `src/dragiter/domain/models/settings.py`
- Parameter groups: `src/dragiter/domain/models/parameters.py`
- Streaming LLM adapter: `src/dragiter/infrastructure/llm/openai_service_ext.py`
- Retry policy and HTTP transport factory: `src/dragiter/infrastructure/llm/openai_runtime.py`
- Legacy non-streaming adapter: `src/dragiter/infrastructure/llm/openai_service.py` (not wired by the CLI; its retry rules differ)

**File formats**

- Prompt model: `src/dragiter/domain/models/prompt_template.py`
- Resource model: `src/dragiter/domain/models/resources.py`
- Output writing: `src/dragiter/application/pipeline/output_writer.py`

**Activity log**

- ActivityProvider protocol: `src/dragiter/domain/ports/activity_provider.py`
- ActivityLogger protocol: `src/dragiter/domain/ports/activity_logger.py`
- Buffered logger: `src/dragiter/application/core/buffered_activity_logger.py`
- File logger: `src/dragiter/application/core/file_activity_logger.py`
- JSONL writer: `src/dragiter/infrastructure/io/io_services.py` → `append_jsonl_to_file`
- Value-settings masking: `src/dragiter/domain/models/value_settings_activity_provider.py`
- Domain producers:
  `src/dragiter/domain/models/{resources,material,loop,prompt_template,chat_sessions,chat_results,application_result}.py`

**Examples**

- Example files: `examples/01_md_sample/`

---

*End of technical reference*
