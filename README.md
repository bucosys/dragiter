## dragiter (Deterministic RAG Iterator)

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

The core philosophy of dragiter is to keep your resources (material, context) and your prompts (instructions) separate.

1. Create a Configuration (Optional but recommended):
   Store your credentials so you don't have to type them out every time.

export DRAGITER_API_KEY="your_api_key"
export DRAGITER_MODEL_NAME="your_preferred_model"

2. Run your first workflow:
   It is highly recommended to use the -s (simulate) flag first to verify your file routing without spending API
   credits.

# Simulate the run

dragiter -s -p prompt\_template.toml -m code\_material.toml

# Execute the run and output to a specific file

dragiter -p prompt\_template.toml -r code\_resource.toml -o final\_report.md

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