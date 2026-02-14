# DeepSearch CLI - Repository Overview

## Project Description
DeepSearch is a command-line deep research tool powered by AI agents. It automates research workflows with parallel processing, source verification, and comprehensive report generation.

## Repository Structure

### Root Directory
- `README.md` - Project documentation and usage guide
- `pyproject.toml` - Python project configuration and dependencies
- `LICENSE` - MIT license
- `.env.example` - Environment variables template

### Core Implementation (`src/deepsearch/`)

#### Main Modules
- `cli.py` - Command-line interface entry point
- `config.py` - Configuration management
- `state.py` - State definitions for research workflow
- `storage.py` - Data persistence layer
- `workflow.py` - Main research workflow orchestration

#### Agents (`src/deepsearch/agents/`)
- `planner.py` - Research planning agent
- `researcher.py` - Information gathering agent
- `reflector.py` - Quality assessment and reflection
- `verifier.py` - Source verification agent
- `writer.py` - Report generation agent

#### Search (`src/deepsearch/search/`)
- `base.py` - Base search interface
- `tavily.py` - Tavily search integration
- `openrouter.py` - OpenRouter search integration

#### Output (`src/deepsearch/output/`)
- `formatters.py` - Output formatting utilities
- `report.py` - Report generation

### Examples (`examples/`)
- Research output examples (arxiv.md, pubmed.md, etc.)

## Key Technologies
- **LangGraph** - Workflow orchestration
- **LangChain** - LLM integration
- **Rich** - Terminal UI
- **Click** - CLI framework
- **Tavily** - Web search API

## Development Commands
```bash
# Install dependencies
uv sync

# Run CLI
deepsearch "your research question"
# or
ds "your research question"

# Code linting
ruff check src/

# Type checking
mypy src/
```

## Configuration
Settings via environment variables (`.env` file):
- `OPENAI_API_KEY` - OpenAI API key
- `TAVILY_API_KEY` - Tavily search API key
- Model and search provider settings
