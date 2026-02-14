# Spec: OpenRouter Logic

## ADDED Requirements

### Requirement: Configure OpenRouter Model
The system MUST allow users to configure models using the `openrouter:` prefix and route these requests to the OpenRouter API.

#### Scenario: User configures an OpenRouter model
- **Given** the configuration specifies `research_model` as `openrouter:google/gemini-2.0-flash-exp:free`
- **And** the `OPENROUTER_API_KEY` is set in the environment
- **When** the system initializes the chat model
- **Then** it should use the `openai` provider with `base_url="https://openrouter.ai/api/v1"`
- **And** it should use the `OPENROUTER_API_KEY` as the API key.

### Requirement: Retrieve OpenRouter API Key
The system MUST retrieve the OpenRouter API key when an OpenRouter model is selected.

#### Scenario: Token retrieval for OpenRouter
- **Given** a model name starting with `openrouter:`
- **When** `get_api_key_for_model` is called
- **Then** it should return the value of `OPENROUTER_API_KEY`.

### Requirement: Document Environment Variables
The system MUST provide an example of the `OPENROUTER_API_KEY` in the `.env.example` file.

#### Scenario: Developer checks example configuration
- **Given** the `.env.example` file
- **Then** it should contain `OPENROUTER_API_KEY=`.
