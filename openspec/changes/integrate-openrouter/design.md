# Design: OpenRouter Integration

## Context
Currently, the system supports OpenAI, Anthropic, and other providers via `langchain`. OpenRouter provides an OpenAI-compatible API that aggregates many models.

## Architecture
- **Model Instantiation**: We will leverage the `openai` provider support in `init_chat_model` but override the `base_url` to `https://openrouter.ai/api/v1` when the model name starts with `openrouter:`.
- **API Key Management**: We will introduce `OPENROUTER_API_KEY` handling in `utils.py`.

## Trade-offs
- **Prefixing**: We use `openrouter:` prefix (e.g., `openrouter:anthropic/claude-3-5-sonnet`) to distinguish from native providers. This allows the user to switch between native and OpenRouter easily.
- **Token Limits**: We may need to update token limit logic if OpenRouter models declare different names that don't match our hardcoded list. For now, we rely on the `model_name` passed to `init_chat_model` (e.g. `anthropic/claude...`) to match existing logic if possible, or accept that token limits might default.

## Alternatives
- **LangChain OpenRouter Class**: access via `ChatOpenAI` is the standard way to use OpenRouter in LangChain.
