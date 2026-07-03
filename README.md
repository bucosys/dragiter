[![License: AGPL v3](https://img.shields.io/badge/License-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![PyPI](https://img.shields.io/pypi/v/dragiter)](https://pypi.org/project/dragiter/)
[![Python](https://img.shields.io/pypi/pyversions/dragiter)](https://pypi.org/project/dragiter/)

## dragiter – Deterministic RAG Iterator. A modular CLI for structured, reproducible LLM workflows.

[WARNING] Status: Alpha / Developer Tool
dragiter is currently in active development. It is highly effective for local, personal workflows and automating local
LLM tasks. However, it is not yet production-ready. Please do not use dragiter in automated CI/CD pipelines, on shared
servers, or to parse untrusted, third-party data due to known limitations in regex handling and dependency injection.

dragiter is a modular command-line interface (CLI) designed to integrate Large Language Models (LLMs) directly into your
automated terminal workflows. It acts as a bridge between your local file system and AI APIs, eliminating "copy-paste
fatigue" by allowing you to chain AI agents exactly like standard Unix pipes.

## Why dragiter?

If you want an AI to review an entire project, manually gathering files, stripping out noise, and pasting them into a
web chat is tedious. dragiter solves this through "Prompt as Code."

* Automated Context Assembly: Use wildcards (like src/\*\*/\*.py) and regex patterns to surgically extract exactly what
  the AI needs to see.
* Version-Controllable Prompts: Define your AI instructions and data context in standard .toml files so your workflows
  are repeatable and shareable.
* Advanced Batch Processing: Feed dragiter a .jsonl loop file to automatically iterate through translation tasks, report
  summaries, or data extraction without writing custom Python scripts.
* Vendor Independence: Switch from cloud providers like OpenAI, Grok, or Google to a completely local, private model
  like Ollama just by changing a single CLI flag.

## Installation

(Assuming you publish to PyPI)
You can install dragiter easily via pip:

pip install dragiter

## Quick Start

The core philosophy of dragiter is to keep your resources (material, context) and your 
prompts (instructions) separate.

The easiest way to explore dragiter is by using the included examples 

### 1. Extract the Examples

First, extract them into your current directory by running:

    dragiter-gen-examples .

You will find the examples in the `examples/` subdirectory. 
To follow along with the first example, navigate into it:

    cd examples/01_md_sample

### 2. Test Safely with Simulation Mode

It is highly recommended to always run a simulation first. 
This allows you to safely verify your workflow and file routing without making actual API calls
or spending your API credits. You can do this by adding the `-s` flag to your command.

Run the simulation by typing:

    dragiter -s -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt

### 3. Run with Ollama
The file `config-ollama.toml` is ready to use out of the box, provided that Ollama is 
installed and running locally with its default settings. When using Ollama it is recommended 
to run the command with the `-v` (verbose) flag:

    dragiter -v -c config-ollama.toml -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt


## Documentation
dragiter comes with a very detailed and well-written manual. 
It is strongly recommended to read it:
    
    # Extract the full documentation
    dragiter-gen-docs .

    # Then read the manual
    less docs/manual.md
    # or open it in your editor / browser

The manual contains many practical examples (code review, batch report analysis, 
marketing copy generation, tool chaining, etc.) and explains advanced features such 
as context window management and JSONL processing in depth.

## Tool Chaining (The Unix Way)

dragiter is built to play nicely with other CLI tools. You can fetch live data and pipe it straight to your AI workflow:

## Acknowledgements

The development of dragiter has been a journey of continuous learning. Bringing this project to life would not have been
possible without the support of some extraordinary tools and communities.

A massive thank you to the AI models Grok and Gemini. As tireless pair-programming partners, your guidance, code
reviews, and structural suggestions were invaluable in adapting the Python code for this project.

Equally important is the global Python community. The rich ecosystem, extensive documentation, and open-source spirit
provide the foundation for tools like dragiter. Thank you to all the developers who make Python such a powerful language
to work with.