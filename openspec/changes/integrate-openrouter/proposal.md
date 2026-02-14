# Integrate OpenRouter

## Goal
Enable the use of OpenRouter as a model provider for the Open Deep Research agent, allowing access to a wider range of models (deepseek, google, etc.) via a unified API.

## Changes
- **Configuration**: Allow `openrouter:` prefix in model configuration.
- **Utils**: Update `get_api_key_for_model` to retrieve `OPENROUTER_API_KEY`.
- **Environment**: Update `.env.example` to include `OPENROUTER_API_KEY`.
- **Model Initialization**: Update `init_chat_model` calls to handle `openrouter:` prefix by configuring the OpenAI provider with OpenRouter's base URL and API key.

## Verification
- Configure the agent to use `openrouter:google/gemini-2.0-flash-exp:free` (or similar).
- Verify that research, summarization, and reporting steps successfully invoke the model via OpenRouter.
