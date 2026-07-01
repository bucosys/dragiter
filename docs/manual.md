dragiter (Deterministic RAG Iterator) Manual
=================================================

dragiter is a modular command-line tool (CLI) designed to integrate working with
large language models (LLMs) into automated workflows. It allows for the
chaining of AI agents similar to pipes in a terminal.

Chapter 1: Getting Started
==========================

Getting Started with Examples
-----------------------------
The easiest way to explore dragiter is by using the included examples.

First, extract them into your current directory by running:

    dragiter-gen-examples .

You will find the examples in the `examples/` subdirectory.  
To follow along with the first example, navigate into it:

    cd examples/01_md_sample



Test Safely with Simulation Mode
--------------------------------
It is highly recommended to always run a simulation first. This allows you to
safely verify your workflow and file routing without making actual API calls
or spending your API credits. You can do this by adding the `-s` flag to your
command.

Run the simulation by typing:

    dragiter -s -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt

What Happens Without Further Configuration?
-------------------------------------------
If you try to run the example without the `-s` flag, you will see an error
similar to this:

    ERROR | dragiter.cli | A critical error occurred: Failed to execute
    application manager run cycle: [ConfigurationValidatorFinding(rule='base_url',
    finding='value not set', description='Path to LLM is mandatory.')]

This is expected. For real LLM requests, dragiter needs connection settings
for an LLM service.

### Using Ollama

The file `config-ollama.toml` is ready to use out of the box, provided that
Ollama is installed and running locally with its default settings.

When using Ollama it is recommended to run the command with the `-v` (verbose)
flag:

    dragiter -v -c config-ollama.toml -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt

**Why use `-v` with Ollama?**  
Local models can take significantly longer to respond than cloud services.
Without the verbose flag you will see no output for quite some time, which can
be confusing. The `-v` flag lets you follow the progress of the request.

### Optional: Making Configuration Permanent

You can optionally copy a working configuration file to the default location
`~/.config/dragiter/config.toml`. After doing so, dragiter will automatically
load the settings without requiring the `-c` flag.

Example:

    mkdir -p ~/.config/dragiter
    cp config-ollama.toml ~/.config/dragiter/config.toml

You can then run the example without `-c`:

    dragiter -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt

Alternatively, you can keep your configuration file in your project folder and
create a symlink:

    ln -s $(pwd)/config-ollama.toml ~/.config/dragiter/config.toml

**Note:** Creating a permanent configuration is convenient if you mostly work
with the same service. If you frequently switch between different providers
(Ollama, Grok, Gemini, etc.), it can be more practical to continue using the
`-c` flag instead.

### Using Cloud Providers (Google, Grok, etc.)

The example directory also contains configuration files for cloud providers,
such as `config-google.toml`.

These files contain placeholder values. Before you can use them, you must edit
the file and insert your own API key.

Once the API key is set, you can run the example with:

    dragiter -v -c config-google.toml -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt

### Alternative: Using Environment Variables

You can also configure dragiter using environment variables. This is useful
when you want to avoid storing credentials in files or when working in
automated environments:

    export DRAGITER_BASE_URL="http://localhost:11434/v1"
    export DRAGITER_MODEL_NAME="qwen3:8b"
    export DRAGITER_API_KEY="ollama"

Once set, you can run the example without the `-c` flag:

    dragiter -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt

### Mixed Configuration

dragiter evaluates configuration sources in the following order (highest priority first):

1. Command-line arguments
2. TOML configuration file
3. Environment variables
4. Hard-coded defaults

This means:
- Values passed via the command line (e.g. `-c`, `--api-key`, `--model-name`) always take precedence.
- Settings from a TOML file are used if they were not already provided on the command line.
- Environment variables (`DRAGITER_*`) are only applied to settings that have not been set by either the command line or a configuration file.

**Practical consequence:**  
You cannot override a value defined in a TOML file using an environment variable. Environment variables are mainly useful when you are **not** using a configuration file, or when you want to provide sensitive values (such as an API key) without storing them in a file.

If you frequently work with different services, it is often more practical to use the `-c` flag to switch between configuration files rather than relying on environment variables.

Chapter 2: Configuration Parameters and Flags
=============================================

dragiter configuration values can be provided in three main ways. The application
reads them in the following order of precedence:

1. Command-line arguments (e.g., --api-key)
2. TOML configuration file (e.g., api_key = "...")
3. Environment variables (e.g., DRAGITER_API_KEY)

General and System Flags
------------------------

### Base Directory

-b, --base-directory Environment: DRAGITER_BASE_DIRECTORY
Meaning: This option defines the base directory for all
relative file paths used in the workflow
(prompt files, resource files, loop files, output directory, etc.).
If not specified, dragiter uses the current working directory.
This flag is especially useful when running dragiter from scripts,
CI/CD pipelines, or when your configuration and data files are located
in a project-specific subdirectory. All relative paths in resources
TOML files (`glob_patterns`) and other file references will be resolved
relative to this base directory.

This is particularly helpful for reproducible workflows, version-controlled projects, and when DRAGITER is called from
different locations (e.g. from a parent directory or via scripts). Once set, dragiter automatically rebases all relative
paths to this directory.

-d, --debug Environment: DRAGITER_DEBUG
Meaning: Enables debug logging to display detailed
internal application processes.

-s, --simulate Environment: DRAGITER_SIMULATE
Meaning: Runs the application in simulation mode. No real
API calls are made, allowing you to safely test
your file routing and prompts.

-v, --verbose Environment: DRAGITER_VERBOSE
Meaning: Enables verbose mode for detailed progress
tracking during execution.

-c, --config-file Environment: DRAGITER_CONFIG
Meaning: Path to a specific TOML configuration file,
overriding the default path.

-h, --help Meaning: Displays the help message and exits the program.


API and Connection Settings
---------------------------
--api-key Environment: DRAGITER_API_KEY
Meaning: The API key used to authenticate with your
chosen LLM service.

--base-url Environment: DRAGITER_BASE_URL
Meaning: The base URL of the AI service endpoint. This is
especially useful if you are routing requests to
a custom, proxy, or local LLM instance.

--model-name Environment: DRAGITER_MODEL_NAME
Meaning: The specific model identifier you want to query
(e.g., gpt-4o, claude-3-5).


Task and Input Control
----------------------

You must provide either a direct task or a prompt template. Note that advanced
input options like material and loop files require the template mode (-p).

[ Choice A: Direct Task Mode ]

-t, --task Environment: DRAGITER_TASK
Meaning: An explicit task description string. If <STDIN>
is provided, it is automatically prepended to
this task string.

[Choice B: Template Mode]

-p, --prompt-file Environment: DRAGITER_PROMPT_FILE
Meaning: Path to a prompt template file (TOML). This file
defines the system instructions and structure.
If <STDIN> is provided, use the [STDIN]
placeholder within the template.

-r, --resource-file Environment: DRAGITER_RESOURCE_FILE
Meaning: Path to the resource definition file (TOML). This
file defines which reference documents, code, or
data chunks are loaded as context for the AI.
Note: Requires -p.

-l, --loop-file Environment: DRAGITER_LOOP_FILE
Meaning: Path to a file (like a text or JSONL file)
containing iteration items. dragiter will loop
through this file line-by-line, executing the
prompt for each item.
Note: Requires -p.


Output Routing and Control
--------------------------
-m, --output-mode Environment: DRAGITER_OUTPUT_MODE
Meaning: Determines the file writing behavior. Valid
single-character options are:
w = Overwrite existing files
a = Append to existing files
x = Exclusive creation (fails if the file
already exists)

-o, --output-file Environment: DRAGITER_OUTPUT_FILE
Meaning: Directs the final AI result to be written into
a specific single file.

-O, --output-directory
Environment: DRAGITER_OUTPUT_DIRECTORY
Meaning: Directs the output results to a specific
directory. This is highly recommended when using
batch processing loops.

-a, --activity-file Environment: DRAGITER_ACTIVITY_FILE
Meaning: Path to write a detailed activity trace and log
of the executed workflow for auditing purposes.

Advanced LLM Settings
---------------------

--max-input-tokens Environment: DRAGITER_MAX_INPUT_TOKENS
Meaning: Sets the maximum number of input tokens allowed
to be transmitted to the AI service. This helps
limit the usage of the context window and
prevents unexpected API costs.

--max-output-tokens Environment: DRAGITER_MAX_OUTPUT_TOKENS
Meaning: Specifies the maximum number of output tokens
that the model is permitted to generate for a
single response.

--chars-per-token Environment: DRAGITER_CHARS_PER_TOKEN
Meaning: A floating-point value indicating the average
number of characters that correspond to one token.
Used internally by dragiter for estimating text
lengths and token consumption.

--temperature Environment: DRAGITER_TEMPERATURE
Meaning: Controls the creativity or unpredictability of
the LLM's responses. A lower value (e.g. 0.0)
ensures deterministic, precise answers, whereas
higher values increase variance.


Fault Tolerance and Rate Limits
-------------------------------

--retry-delay Environment: DRAGITER_RETRY_DELAY
Meaning: Determines the pause duration in seconds that
dragiter waits before retrying a failed API
call (e.g. when encountering rate limits).

--max-retry Environment: DRAGITER_MAX_RETRY
Meaning: Configures the maximum number of times (<num>)
dragiter will retry a failed API call before
aborting the entire execution process.

**A Note on Best Practices**
Because these advanced parameters dictate the fundamental behaviour, connection limits,
and pacing of your AI workflow, they rarely change between individual runs.
It is highly recommended to define these values permanently within your `config.toml`
file rather than passing them via the command line every time.


Chapter 3: Using Material and Prompt Templates
==============================================

To harness the full power of dragiter, you need to understand how to feed it
context and how to instruct the AI. This is done using Material files and
Prompt Templates, both of which are written in standard TOML format.

1. Defining the resources (Your Knowledge Base)

----------------------------------------------
The resource file tells dragiter which files to read and how to divide their
content into digestible chunks for the AI.

Selecting Files:
Inside the resource TOML file, you define configuration sections. Each section
can have a "glob_patterns" list. You can point directly to concrete files or
use wildcards to include entire folders, such as ["docs/manual.md"],
["data/**/*.csv"] or ["*.md"].

The optional "base_directory" key allows you to set a section-specific root
path. It overrides the global --base-directory (-b) flag for that section only.

Regex Chunking:
To prevent sending massive, unformatted walls of text to the AI, you can
provide a "regex_pattern". This splits the documents into logical sections.
For example, a regex pattern like '(^#+\s+.*$)' will chunk Markdown files by
their headers. You can also use "exclude_filters" and "include_filters" to
strictly control which chunks are kept.

2. Creating the Prompt Template (Your Instructions)

---------------------------------------------------
The prompt file dictates how the AI should behave and how the material is
presented. It is divided into specific blocks:

The System Block:
Defined as [system], this block contains the "instruction" variable. Here you
define the AI's persona or core rules.

The Task Block:
Defined as [task], this block contains the main prompt structure. It is usually
broken down into:

- "first": An introductory text.
- "material": A formatting template for how each chunk of context is presented.
- "synthesis": The final question or command for the AI.

The Output Block:
Defined as [output], this block can contain "output_filename_schema" and
"output_delimiter" to control how resulting files are named and separated.

3. Connecting Content with Dynamic Placeholders

-----------------------------------------------
dragiter uses reserved keywords and bracketed placeholders to inject your data
dynamically during execution.

Global Keywords:
Use [MATERIAL] to specify exactly where your reference files should be
injected. Use [STDIN] to define the target location for standard input data.

Chunk Variables:
Inside the "material" section of your task block, you can format each piece of
reference text using variables like:

- {CHUNK_NUM_ID:04d} for a sequential ID number.
- {CHUNK_FILE_NAME} for the source file name.
- {CHUNK_SECTION_NAME} for the section name.
- {CHUNK_SECTION_NUM_ID} for the section number.
- {CHUNK_CONTENT} for the actual text extracted from the file.

Loop Variables:
If you are running a batch process using a loop file, place the {LOOP_CONTENT}
variable inside your "synthesis" block. dragiter will replace this placeholder with
the current line (or JSON fields) from your loop file for each iteration.


Chapter 4: Practical Examples and Concrete Jobs
===============================================

Now that you understand how to configure materials, prompts, and loops, let us
look at two real-world scenarios where dragiter can automate complex workflows.


Scenario 1: Automated Code Security Audits
------------------------------------------
Imagine a development team needs to review a legacy C codebase for potential
memory leaks and security vulnerabilities. Manually reading thousands of lines
of code is error-prone and time-consuming.

The Setup:

* Resource: The resource TOML file is configured to scan the "src" folder for
  all "*.c" and "*.h" files. A regex pattern is applied to chunk the code
  block by block, specifically splitting the text at every function definition.
  This ensures the AI evaluates the code one function at a time.
* Prompt: The prompt TOML file defines the [system] instruction as a
  "Senior Security Auditor." The [task] block is set up to inject the
  {CHUNK_CONTENT} and asks the AI to identify any buffer overflows or memory
  mismanagement, formatting the output as a Markdown table.
* Loop: No loop file is needed here; the AI processes the provided material
  chunk by chunk based on the prompt's internal logic.

The Command:
dragiter -p audit_prompt.toml -r legacy_code_resource.toml -O ./audit_results

Result:
dragiter processes the source code functions and deposits the individual analysis
reports into the "audit_results" directory, giving the team a structured
security overview of their legacy code.


Scenario 2: Batch Processing Quarterly Reports
----------------------------------------------
A financial analyst has a folder filled with dense text reports spanning
several years. They need to extract specific performance metrics without
reading every page.

The Setup:

* Resource: The resource TOML file points to a "reports" directory, loading all
  "*.txt" files. A regex pattern chunks the documents by major section headers
  (e.g., "Introduction", "Financials", "Outlook").
* Loop: The analyst creates a simple text file named "metrics_loop.txt"
  containing three lines: "Operating Costs", "Net Profit", and
  "Year-over-Year Growth".
* Prompt: The prompt template uses the {LOOP_CONTENT} variable in the
  synthesis block. It instructs the AI: "Scan the provided reference material
  and extract the exact figures and a brief summary specifically for
  {LOOP_CONTENT}."

The Command:
dragiter -p extract_prompt.toml -r quarterly_reports.toml -l metrics_loop.txt \
-o final_summary.txt -m a

Result:
dragiter iterates through the loop file. First, it asks the AI to find
"Operating Costs" across all reports. Next, it asks for "Net Profit", and
finally "Year-over-Year Growth". Because the analyst used the "-M a" (append)
flag, dragiter writes all three consolidated answers into a single, highly
readable "final_summary.txt" document.


Chapter 5: Advanced Batch Processing with JSONL
===============================================

While simple text files are great for looping through single variables (using
the {LOOP_CONTENT} placeholder), dragiter also natively supports JSON Lines (JSONL)
files for more complex batch processing.

By using a JSONL file, you can pass multiple structured data points into your
prompt during each iteration. dragiter automatically parses the JSON objects and
makes every key available as a dynamic placeholder in your prompt template.


Scenario 3: Localized Content Generation
----------------------------------------
Imagine a marketing manager needs to take a master product manual and generate
localized, region-specific sales summaries in different languages and tones.

The Setup:

- Resource: The resource TOML file points to "master_manual.md", extracting the
  core features and specifications of the new product.

- Loop File: The manager creates a file named "target_markets.jsonl". Each line
  is a valid JSON object containing specific parameters for that iteration:
  {"language": "German", "region": "DACH", "tone": "formal"}
  {"language": "Spanish", "region": "Latin America", "tone": "enthusiastic"}
  {"language": "English", "region": "Gen Z", "tone": "casual and trendy"}

- Prompt: The prompt template uses these exact JSON keys as placeholders in the
  synthesis block. It instructs the AI:
  "Using the provided product material, write a {tone} marketing summary
  targeted at the {region} demographic. The final output MUST be written
  entirely in {language}."

The Command:
dragiter -p localized_prompt.toml -r master_manual.toml -l target_markets.jsonl \
-O ./campaigns

Result:
dragiter loops through the JSONL file. In the first iteration, it replaces the
placeholders to request a formal German summary for the DACH region. In the
next, it requests an enthusiastic Spanish version. Because the "-O" flag was
used, dragiter deposits three distinct, perfectly tailored marketing documents
into the "campaigns" directory.


Chapter 6: Tool Chaining and External Data Fetching
===================================================

Because dragiter is built around the Unix philosophy of doing one thing well, it is
designed to be a seamless part of larger automation pipelines. You are not
limited to the files already sitting on your hard drive; you can use external
tools to fetch live data, save it locally, and immediately pass it to dragiter for
AI-driven analysis.

By combining dragiter with standard command-line utilities like "wget", "curl", or
database CLI clients, you can build powerful, autonomous workflows.


Scenario 4: Competitor Website Analysis via wget
------------------------------------------------
Imagine you want to track changes to a competitor's pricing page and have an AI
summarize the differences or current tiers every Monday morning.

The Setup:
First, you use "wget" or "curl" in a simple shell script to download the target
webpage and save it as a text or HTML file.
Next, your dragiter resources TOML file is configured to read this newly downloaded
file. You might use a regex pattern in the material config to strip away
massive HTML headers or isolate the specific <body> tags.

The Workflow Script:
#!/bin/bash

    # 1. Fetch the live data
    curl -s https://example-competitor.com/pricing > /tmp/current_pricing.html

    # 2. Run dragiter to analyze the downloaded file
    dragiter -p summarize_pricing.toml -r web_resources.toml -o pricing_report.txt

Result:
The script automatically pulls the freshest data from the internet, feeds it
into your local dragiter environment, and generates a clean, human-readable summary
of the competitor's pricing strategy.


Scenario 5: Database Export and Sentiment Analysis
--------------------------------------------------
Customer support teams often have thousands of feedback tickets trapped in a
relational database. dragiter can be chained to database export tools to analyze
this data on the fly.

The Setup:
You have a PostgreSQL or MySQL database containing user reviews. You use the
database's CLI tool to export yesterday's reviews into a CSV or JSONL file.

The Workflow Script:
#!/bin/bash

    # 1. Export data from the database to a file
    psql -U admin -d support_db -c "COPY (SELECT review_text FROM tickets \
         WHERE date = CURRENT_DATE - 1) TO STDOUT WITH CSV;" > /tmp/daily_reviews.csv

    # 2. Process the exported data with dragiter
    dragiter -p sentiment_prompt.toml -r review_resources.toml -o daily_sentiment.md

Result:
The database query dumps the raw data into a temporary file. dragiter instantly
picks up that file, chunks the reviews, asks the AI to identify negative
trends or bugs, and writes a comprehensive Markdown report for the product
team's morning meeting.


Chapter 7: Connecting to Different AI Engines
=============================================

One of the greatest strengths of dragiter is that it does not lock you into a
single ecosystem. Because the tool is built to communicate with OpenAI-compatible
API endpoints, you can easily swap out the underlying brain of your workflow
just by changing a few configuration parameters.

Whether you want to use the latest frontier models from Google or xAI (Grok),
or run fully local, privacy-respecting open-source models, dragiter handles the
connection seamlessly.


The Magic Flags: Base URL and Model Name
----------------------------------------
To switch AI engines, you primarily rely on three configuration flags (which
can also be set in your config.toml or environment variables):

* --base-url   : This tells dragiter exactly where to send your prompt payload.
* --model-name : This tells the receiving server which specific model to use.
* --api-key    : The authentication token for the service.

Scenario 6: Zero-Cost, Private Local AI with Ollama
---------------------------------------------------
If you are processing highly sensitive corporate data or simply want to avoid
API costs, you can run LLMs locally on your own hardware using a tool like
Ollama. Ollama provides a local API endpoint that dragiter can talk to.

The Setup:
First, you install Ollama on your machine and download a model, such as Meta's
Llama 3 or Mistral, using your terminal: "ollama run llama3".

The Command:
Once Ollama is running in the background, you instruct dragiter to bypass the cloud
and send the data to your localhost:

    dragiter -p code_review.toml -r local_files.toml --base-url "http://localhost:11434/v1" \
         --model-name "llama3" --api-key "dummy-key"

Result:
dragiter packages your prompt and material, but instead of sending it over the open
internet, it routes it to your local machine's port 11434. The local Llama 3
model processes the data, completely off the grid.


Scenario 7: Tapping into Alternative Cloud Providers (Grok, Google, etc.)
------------------------------------------------------------------------
Many modern AI providers offer "OpenAI-compatible" API endpoints. This means
their servers speak the exact same technical language as OpenAI, allowing tools
like dragiter to connect instantly without needing custom code.

For Grok (xAI):
If you want to use xAI's Grok model, you simply point the Base URL to their
endpoint and provide your xAI API key.

    dragiter -p analysis.toml -r data.toml --base-url "https://api.x.ai/v1" \
         --model-name "grok-beta" --api-key "YOUR_XAI_KEY"

For Google Vertex AI or Other Services:
While some services use their own unique SDKs, many offer compatibility layers
or intermediary proxy gateways (like LiteLLM). As long as you have the
compatible base URL, you can route dragiter to virtually any model on the market:

    dragiter -p creative_prompt.toml -r context.toml --base-url "YOUR_PROVIDER_BASE_URL" \
         --model-name "gemini-1.5-pro" --api-key "YOUR_API_KEY"

By keeping the application logic separate from the LLM provider, dragiter ensures
your automated workflows are future-proof. If a faster, cheaper, or smarter
model is released tomorrow, you only need to change a single line in your
configuration file to upgrade your entire toolchain.




Chapter 8: Acknowledgements and Special Thanks
==============================================



The development of dragiter (Artificial Intelligence Working Kit) has been a
journey of continuous learning and exploration. Bringing this project to life
would not have been possible without the support of some extraordinary tools
and communities.

Thanks to Grok and Gemini:
A massive and special thank you goes to the AI models Grok and Gemini. Your
guidance, code reviews, and structural suggestions were invaluable. You not
only helped in writing, debugging, and adapting the Python code for this
project, but you also played a crucial role in elevating my own Python skills.
Acting as tireless pair-programming partners, you helped turn the vision for
this CLI tool into a working reality.

Thanks to the Python Community:
Equally important is the global Python community. The rich ecosystem of
standard libraries, the extensive documentation, and the unwavering open-source
spirit provide the foundation upon which tools like dragiter are built. Thank you
to all the developers, contributors, and enthusiasts who continue to make
Python such an accessible and powerful language to work with.

Happy automating!
