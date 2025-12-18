FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Install dependencies first
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the source code
COPY converter.py mock_openai_server.py ./

# Expose the Ollama API port
EXPOSE 11434

CMD ["uv", "run", "converter.py"]
