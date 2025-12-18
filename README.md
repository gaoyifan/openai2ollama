# OpenAI to Ollama API Converter

A proxy server that transforms the OpenAI API into the Ollama API, enabling tools and clients built for Ollama to use OpenAI models (or any OpenAI-compatible endpoint).

## Features

- **Standard APIs**: Implements `/api/tags`, `/api/show`, and `/api/chat`.
- **Streaming**: Full support for real-time response streaming (SSE).
- **Tools**: Support for function calling/tools, translating between OpenAI and Ollama formats.
- **UV Powered**: Managed with `uv` for fast dependency and environment management.

## Project Structure

- `converter.py`: The core FastAPI application serving the Ollama API.
- `mock_openai_server.py`: A local mock server for testing OpenAI API interactions.
- `test_end_to_end.py`: Integration tests using the official Ollama Python client.

## Quick Start

### 1. Installation

Ensure you have [uv](https://github.com/astral-sh/uv) installed.

```bash
uv sync
```

### 2. Configuration

Set your OpenAI API credentials and endpoint:

```bash
export OPENAI_API_KEY=your_api_key
export OPENAI_API_BASE=https://api.openai.com/v1
```

### 3. Run the Converter

```bash
uv run python converter.py
```

The converter will be available at `http://127.0.0.1:11434`.

## Testing

To run the end-to-end tests locally:

1. **Start the Mock OpenAI Server**:
   ```bash
   uv run python mock_openai_server.py
   ```

2. **Start the Converter** (pointing to the mock server):
   ```bash
   export OPENAI_API_BASE=http://127.0.0.1:8001/v1
   export OPENAI_API_KEY=dummy
   uv run python converter.py
   ```

3. **Run the Test Script**:
   ```bash
   uv run python test_end_to_end.py
   ```

## License

MIT
