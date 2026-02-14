# Project Context

## Purpose
Open Deep Research is a configurable, fully open-source deep research agent that works across multiple model providers, search tools, and MCP (Model Context Protocol) servers. It facilitates automated research with parallel processing and comprehensive report generation.

## Tech Stack
- **Language**: Python >= 3.10 (managed by `uv`)
- **Orchestration**: LangGraph, LangChain
- **LLM Providers**: OpenAI, Anthropic, Google, Groq, DeepSeek, generic MCP models
- **Search**: Tavily, DuckDuckGo, Exa, Arxiv, PubMed, Native provider search (OpenAI/Anthropic)
- **Database/Storage**: InMemory (for development), Supabase (optional/integrated)
- **External Tools**: Model Context Protocol (MCP) servers

## Project Conventions

### Code Style
- **Linting**: `ruff` is used for linting (configuration in `pyproject.toml`).
- **Formatting**: `ruff` handles formatting.
- **Type Checking**: `mypy` is used for static type checking.
- **Docstrings**: Google style docstrings are required (enforced by `ruff`).
- **Imports**: Sorted by `isort` (via `ruff`).

### Architecture Patterns
- **Graph-Based**: Core logic is implemented as a LangGraph state machine (`src/open_deep_research/deep_researcher.py`).
- **State Management**: TypedDict/Pydantic models in `state.py` define the data flow.
- **Configuration**: Centralized in `configuration.py` (Pydantic model).
- **Tooling**: Tools are defined functionally or via LangChain/MCP adapters.

### Testing Strategy
- **Framework**: `pytest`
- **Unit Tests**: Locate in `tests/`
- **Evaluation**: Specialized evaluation scripts (`tests/run_evaluate.py`) for deep research benchmarking.

### Git Workflow
- **Development**: Feature branches.
- **Commit Messages**: Clear, descriptive messages are expected.
- **PRs**: Required for changes.

## Domain Context
- **Deep Research**: The system performs iterative research, "thinking" (reflection), and synthesis.
- **Recursion**: Can spawn sub-researchers (recursive depth) or parallel threads.
- **MCP**: Uses the Model Context Protocol to extend capabilities without changing core code.

## Important Constraints
- **Token Limits**: Must handle context window limits (truncation/summarization logic exists in `utils.py`).
- **API Costs**: Extensive research can be expensive; concurrency limits and depth controls are critical.
- **Async**: The core is asynchronous (`async/await`) to handle parallel I/O.

## External Dependencies
- **LLM APIs**: OpenAI, Anthropic, Google Vertx/GenAI, etc.
- **Search APIs**: Tavily, Exa, etc.
- **Supabase**: Optional integration for state/auth.
