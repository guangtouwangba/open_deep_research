.PHONY: all install dev lint test clean help setup start stop check format openrouter

# Default target
all: help

# Help command
help:
	@echo "Open Deep Research Makefile"
	@echo ""
	@echo "Quick Start:"
	@echo "  make install        - Install dependencies (then use 'ds' command)"
	@echo "  make setup          - Full setup: install deps + create .env file"
	@echo ""
	@echo "Usage (after install):"
	@echo "  ds \"your topic\"                        - Run a research task"
	@echo "  ds \"your topic\" --deep                 - Deep/comprehensive research"
	@echo "  ds \"topic\" --depth quick --output r.md  - With options"
	@echo "  ds status                              - Check research status"
	@echo "  ds config show                         - Show configuration"
	@echo ""
	@echo "Server Commands:"
	@echo "  make dev            - Start LangGraph development server"
	@echo "  make start          - Start server (alias for dev)"
	@echo "  make start-search   - Start with specific search API (SEARCH=openrouter)"
	@echo "  make openrouter     - Quick start with OpenRouter search"
	@echo "  make stop           - Stop the running server"
	@echo ""
	@echo "Development Commands:"
	@echo "  make lint           - Run code linting"
	@echo "  make format         - Format code with ruff"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Clean up cache files"
	@echo "  make check          - Check OpenRouter configuration"
	@echo ""

# Setup environment
setup:
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example. Please edit .env with your API keys."; \
	else \
		echo ".env file already exists."; \
	fi
	@echo "Installing dependencies with uv..."
	@if command -v uv >/dev/null 2>&1; then \
		uv sync; \
	else \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		uv sync; \
	fi
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "1. Edit .env file and add your API keys (OPENROUTER_API_KEY, etc.)"
	@echo "2. Run: ds \"your research topic\""
	@echo ""

# Install dependencies — quick start entry point
install:
	@echo "Installing dependencies..."
	@if command -v uv >/dev/null 2>&1; then \
		uv sync; \
	else \
		echo "'uv' not found. Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		uv sync; \
	fi
	@echo ""
	@echo "Done! You can now use the 'ds' command:"
	@echo "  ds \"your research topic\"          # start researching"
	@echo "  ds \"topic\" --deep                 # comprehensive research"
	@echo "  ds --help                          # see all options"
	@echo ""

# Run development server
dev:
	@echo "Starting LangGraph development server..."
	@echo "API: http://127.0.0.1:2024"
	@echo "Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024"
	@echo ""
	@bash -c ' \
		export OPENROUTER_API_KEY=$$(grep "^OPENROUTER_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export TAVILY_API_KEY=$$(grep "^TAVILY_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export OPENAI_API_KEY=$$(grep "^OPENAI_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export ANTHROPIC_API_KEY=$$(grep "^ANTHROPIC_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export GOOGLE_API_KEY=$$(grep "^GOOGLE_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export LANGSMITH_API_KEY=$$(grep "^LANGSMITH_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export LANGSMITH_PROJECT=$$(grep "^LANGSMITH_PROJECT=" .env 2>/dev/null | cut -d= -f2-); \
		export LANGSMITH_TRACING=$$(grep "^LANGSMITH_TRACING=" .env 2>/dev/null | cut -d= -f2-); \
		if [ -z "$$LANGSMITH_TRACING" ]; then export LANGSMITH_TRACING=false; fi; \
		if command -v uv >/dev/null 2>&1; then \
			uvx --no-env-file --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking; \
		else \
			echo "Error: uv is not installed. Please install it: https://docs.astral.sh/uv/getting-started/installation/"; \
			exit 1; \
		fi \
	'

# Alias for dev
start: dev

# Start with specific search API
start-search:
	@if [ -z "$(SEARCH)" ]; then \
		echo "Usage: make start-search SEARCH=openrouter"; \
		echo "Available: tavily, openrouter, anthropic, openai, none"; \
		exit 1; \
	fi
	@echo "Starting with search_api=$(SEARCH)..."
	@bash -c ' \
		export OPENROUTER_API_KEY=$$(grep "^OPENROUTER_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export TAVILY_API_KEY=$$(grep "^TAVILY_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export OPENAI_API_KEY=$$(grep "^OPENAI_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export ANTHROPIC_API_KEY=$$(grep "^ANTHROPIC_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export GOOGLE_API_KEY=$$(grep "^GOOGLE_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export LANGSMITH_API_KEY=$$(grep "^LANGSMITH_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export LANGSMITH_PROJECT=$$(grep "^LANGSMITH_PROJECT=" .env 2>/dev/null | cut -d= -f2-); \
		export LANGSMITH_TRACING=$$(grep "^LANGSMITH_TRACING=" .env 2>/dev/null | cut -d= -f2-); \
		if [ -z "$$LANGSMITH_TRACING" ]; then export LANGSMITH_TRACING=false; fi; \
		export SEARCH_API=$(SEARCH); \
		if command -v uv >/dev/null 2>&1; then \
			uvx --no-env-file --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking; \
		else \
			echo "Error: uv is not installed."; \
			exit 1; \
		fi \
	'

# Quick start with OpenRouter
openrouter: check
	@echo "Starting with OpenRouter search..."
	@bash -c ' \
		export OPENROUTER_API_KEY=$$(grep "^OPENROUTER_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export TAVILY_API_KEY=$$(grep "^TAVILY_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export OPENAI_API_KEY=$$(grep "^OPENAI_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export ANTHROPIC_API_KEY=$$(grep "^ANTHROPIC_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export GOOGLE_API_KEY=$$(grep "^GOOGLE_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export LANGSMITH_API_KEY=$$(grep "^LANGSMITH_API_KEY=" .env 2>/dev/null | cut -d= -f2-); \
		export LANGSMITH_PROJECT=$$(grep "^LANGSMITH_PROJECT=" .env 2>/dev/null | cut -d= -f2-); \
		export LANGSMITH_TRACING=$$(grep "^LANGSMITH_TRACING=" .env 2>/dev/null | cut -d= -f2-); \
		if [ -z "$$LANGSMITH_TRACING" ]; then export LANGSMITH_TRACING=false; fi; \
		export SEARCH_API=openrouter; \
		if command -v uv >/dev/null 2>&1; then \
			uvx --no-env-file --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking; \
		else \
			echo "Error: uv is not installed."; \
			exit 1; \
		fi \
	'

# Check OpenRouter configuration
check:
	@echo "Checking configuration..."
	@$(eval ENV_API_KEY := $(shell grep -s '^OPENROUTER_API_KEY=' .env | cut -d '=' -f2 | head -1))
	@if [ -z "$(OPENROUTER_API_KEY)" ] && [ -z "$(ENV_API_KEY)" ]; then \
		echo "OPENROUTER_API_KEY: ✗ Not set"; \
		echo ""; \
		echo "Please set your OpenRouter API key:"; \
		echo "  export OPENROUTER_API_KEY=your_key_here"; \
		echo ""; \
		echo "Or add it to .env file:"; \
		echo "  echo 'OPENROUTER_API_KEY=your_key_here' >> .env"; \
		exit 1; \
	else \
		echo "OPENROUTER_API_KEY: ✓ Set"; \
	fi

# Stop server
stop:
	@echo "Stopping LangGraph server..."
	@lsof -ti:2024 | xargs kill -9 2>/dev/null || true
	@echo "Server stopped"

# Run linting
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff format .
	uv run ruff check --fix .

# Run tests
test:
	uv run pytest

# Clean up
clean:
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "Cleanup complete!"
