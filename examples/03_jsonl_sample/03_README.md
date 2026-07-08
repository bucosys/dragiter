# Getting Started with Example 03

This example demonstrates a loop file value mixin 


## Preparation
First, open your terminal and navigate to the example directory by typing:

    cd examples/03_md_sample

It is highly recommended to run a simulation first.

## Step 1 - Simulation (Dry Run)
Run the simulation by typing:
    
    dragiter -s -p 03_prompt_marketing.toml -r 03_resource_marketing.toml -l 03_loop_target_groups.jsonl

You might add output parameters like
    
    dragiter -s -p 03_prompt_marketing.toml -r 03_resource_marketing.toml -l 03_loop_target_groups.jsonl -o 03_output.txt -a 03_activity.txt

## Step 2 - Processing with Ollama
Once you confirm the simulation output looks correct, run the actual process by removing the -s flag:

    dragiter -v -c config-ollama.toml -p 03_prompt_marketing.toml -r 03_resource_marketing.toml -l 03_loop_target_groups.jsonl -o 03_output.txt -a 03_activity.txt

Start from outside example directory:

    dragiter -s -d -v -b ./examples/03_jsonl_sample -c config-ollama.toml -p 03_prompt_marketing.toml -r 03_resource_marketing.toml -l 03_loop_target_groups.jsonl -o ${PWD}/03_output.txt -a ${PWD}/03_activity.txt

## Next steps
To avoid typing your API key and model name every time, you can store them in a configuration file. By default, dragiter
looks for a default user config file at ~/.config/dragiter/config.toml.

If you prefer to keep your actual configuration file in a specific project folder or under version control, you can
create a soft link (symlink) from the default user configuration path to your real file.

To create the symbolic link, use the ln command by typing:

    ln -s /path/to/your/real/config.toml ~/.config/dragiter/config.toml

This allows dragiter to automatically find your settings without needing to move the file or type the -c flag every time
you run a command.

Alternatively, you can use the -c flag to point to a specific TOML config file, or use environment variables
like DRAGITER_API_KEY.

For more detailed explanations, advanced configuration options, and examples for professional services such as
Google Gemini, Grok (xAI), or other providers, please refer to the full manual.

You can extract the documentation by running:

    dragiter-gen-docs .

The manual will be created in the `docs/` directory. It contains comprehensive guidance on prompt templates,
resource configuration, token management, batch processing with JSONL, and tool chaining.