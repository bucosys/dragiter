# Getting Started with Example 01

This example demonstrates a basic Markdown analysis workflow.

## Step 1. Open your terminal window and navigate into the example directory

    cd examples/01_md_sample

## Step 2. Run in simulation mode first (highly recommended)

It is highly recommended to always run a simulation first. This allows you to
safely verify your workflow and file routing without making actual API calls
or spending your API credits. You can do this by adding the `-s` flag to your
command.

Run the simulation by typing:

    dragiter -s -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt

## Step 3. Using Ollama

The file `config-ollama.toml` is ready to use out of the box, provided that
Ollama is installed and running locally with its default settings.

When using Ollama it is recommended to run the command with the `-v` (verbose)
flag:

    dragiter -v -c config-ollama.toml -p 01_prompt_md.toml -r 01_resource_md.toml -l 01_loop_md.txt

## Further Information

For more detailed explanations, advanced configuration options, and examples for professional services such as
Google Gemini, Grok (xAI), or other providers, please refer to the full manual.

You can extract the documentation by running:

    dragiter-gen-docs .

The manual will be created in the `docs/` directory. It contains comprehensive guidance on prompt templates,
resource configuration, token management, batch processing with JSONL, and tool chaining.