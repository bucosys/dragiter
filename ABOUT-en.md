# About dragiter (Deterministic RAG Iterator)

dragiter is a modular command-line tool (CLI) designed to integrate working with large language models (LLMs) into automated workflows. Inspired by the Unix philosophy ("Do one thing and do it well"), it allows for the chaining of AI agents similar to pipes in a terminal.

## Core Features

* **Modularity**: Agents and components can be flexibly combined to create tailor-made solutions.
* **Context Management**: AiWK enables the dynamic loading of reference materials. Users can specify specific files or folders and precisely filter content using regex patterns to inject them as context into the AI prompt.
* **Automation**: The tool supports batch processing (loops), allowing recurring tasks to be executed efficiently across multiple inputs.
* **Flexibility**: It offers a unified interface for various AI backends, such as OpenAI or Google Vertex AI.

## Use Cases

dragiter is particularly suitable for developers and technical users who:
* Want to create automated code analyses or documentation.
* Need to generate content based on specific project contexts.
* Want to automate complex query scenarios that require structured data or file contents as a knowledge base.

## Technology

The tool is written in Python (>= 3.11) and relies on a lightweight, extensible architecture. It uses modern libraries such as `tomllib` for configuration and the SDKs of the respective AI providers.