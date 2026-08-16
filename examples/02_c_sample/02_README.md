# Getting Started with Example 02

This example demonstrates a C code security analysis workflow.

> **Important:**
> In this example, `sequential_processing` is enabled in the prompt file (`02_prompt_c_sample.toml`).
> This means each code chunk (typically a function) is sent to the LLM individually.
> This approach leads to significantly deeper and more reliable analysis compared to
> sending the entire codebase in one request.

## Preparation
Open your terminal and navigate to the example directory:
    cd examples/02_c_sample

It is highly recommended to run a simulation first.

## Step 1 - Simulation w/o using LLM
Run the simulation by typing:

    dragiter -s -p 02_prompt_c_sample.toml -r 02_resource_c_sample.toml

## Step 2 - Processing with Ollama
Once you confirm the simulation output looks correct, run the actual process by removing the -s flag:

    dragiter -v -c config-ollama.toml -p 02_prompt_c_sample.toml -r 02_resource_c_sample.toml


For more detailed explanations, advanced configuration options, and examples for professional services such as
Google Gemini, Grok (xAI), or other providers, please refer to the full manual.

You can extract the documentation by running:

    dragiter-gen-docs .

The manual will be created in the `docs/` directory. It contains comprehensive guidance on prompt templates,
resource configuration, token management, batch processing with JSONL, and tool chaining.