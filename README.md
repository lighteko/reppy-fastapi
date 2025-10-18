# Reppy FastAPI - RAG Pipeline with LangChain

Production-ready RAG pipeline for Reppy AI fitness coaching using LangChain, AgentExecutor, and LCEL.

## Features

- ✅ **Dual Execution Modes**
  - **Mode A**: Automatic routing to appropriate prompts based on input analysis
  - **Mode B**: Direct execution with specified prompt
  
- ✅ **Dynamic Prompt System**
  - YAML-based prompts auto-discovered from `prompts/` directory
  - Three default prompts: `chat_response`, `generate_program`, `update_routine`
  - Extensible without code changes

- ✅ **LangChain Integration**
  - Tool-calling agents with structured tools
  - LCEL pipelines with preprocessing, validation, and postprocessing
  - AgentExecutor with configurable iterations and timeouts

- ✅ **RAG Components**
  - Qdrant vector database for exercise search and user memory
  - OpenAI embeddings for semantic search
  - MMR support for diversity (configurable)

- ✅ **Domain Tools**
  - `calculate_one_rep_max`: Calculate 1RM from workout history
  - `get_exercise_details`: Fetch exercise information
  - `get_exercise_performance_records`: Get user's performance history
  - `recall_user_memory`: Search user's long-term memory
  - `find_relevant_exercises`: Semantic exercise search
  - `get_active_routines`: Fetch user's current workout routines

- ✅ **Validation & Safety**
  - Pydantic v2 schemas for response validation
  - Domain guards for exercise and set type codes
  - Automatic retry on parsing errors

- ✅ **Observability**
  - Loguru-based logging with rotation
  - Custom callback handlers for tool/LLM tracking
  - Optional LangSmith tracing integration

- ✅ **Production-Ready**
  - FastAPI with async support
  - AWS Lambda consumer for SQS job processing
  - Health checks for all dependencies
  - Comprehensive test suite

## Architecture

```
┌─────────────┐
│   FastAPI   │  Mode A: POST /api/v1/route
│   Routers   │  Mode B: POST /api/v1/run
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Action Router   │  Routes to: chat_response, generate_program, update_routine
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Prompt Loader    │  Loads YAML prompts dynamically
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Agent Builder   │  Creates LangChain tool-calling agent
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Agent Executor   │  Runs agent with tools
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  LCEL Pipeline   │  Preprocess → Execute → Parse → Validate → Postprocess
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   Validation     │  Schema validation + domain guards
└──────────────────┘
```

## Project Structure

```
reppy-fastapi/
├── prompts/                  # YAML prompt files (auto-discovered)
│   ├── chat_response.yaml
│   ├── generate_program.yaml
│   └── update_routine.yaml
├── src/
│   ├── config/              # Configuration singleton
│   │   ├── __init__.py
│   │   └── baseconfig.py
│   ├── infra/               # Infrastructure clients
│   │   ├── __init__.py
│   │   ├── qdrant_client.py
│   │   └── express_client.py
│   ├── common/              # Core RAG components
│   │   ├── __init__.py
│   │   ├── prompts.py       # Dynamic YAML loader
│   │   ├── rag_retriever.py # Qdrant-backed retriever
│   │   ├── tools.py         # LangChain tools
│   │   ├── validation.py    # Pydantic schemas
│   │   ├── observability.py # Logging & callbacks
│   │   ├── lcel_pipeline.py # LCEL assembly
│   │   ├── agent_builder.py # Agent construction
│   │   ├── executor.py      # AgentExecutor wrapper
│   │   ├── action_router.py # Pattern-based routing
│   │   └── action_router_llm.py # LLM-based routing
│   ├── api/                 # FastAPI endpoints
│   │   ├── __init__.py
│   │   └── routers.py
│   ├── consumer/            # AWS Lambda handler
│   │   ├── __init__.py
│   │   └── lambda_handler.py
│   └── app.py               # FastAPI app
├── tests/                   # Test suite
│   ├── test_prompts.py
│   ├── test_router.py
│   ├── test_llm_router.py
│   ├── test_qdrant_client.py
│   ├── test_express_client.py
│   ├── test_validation.py
│   └── test_retriever.py
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.11+
- OpenAI API key
- **Qdrant Cloud account** (or local Qdrant for development)
- Express API server

> 💡 **Using Remote Qdrant**: This project is designed to work with Qdrant Cloud. See [QDRANT_SETUP.md](QDRANT_SETUP.md) for detailed setup instructions.

## Installation

1. **Clone the repository**

```bash
cd reppy-fastapi
```

2. **Create virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment**

```bash
cp env.example .env
# Edit .env with your configuration
```

**Required configuration:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `QDRANT_URL`: Your Qdrant Cloud cluster URL (e.g., `https://xxxxx.cloud.qdrant.io`)
- `QDRANT_API_KEY`: Your Qdrant Cloud API key
- `EXPRESS_BASE_URL`: Express API server URL

**Example .env:**
```env
OPENAI_API_KEY=sk-your-openai-key
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
EXPRESS_BASE_URL=http://localhost:3000
```

> 📘 See [QDRANT_SETUP.md](QDRANT_SETUP.md) for detailed Qdrant configuration

## Usage

### Running the FastAPI Server

```bash
python src/app.py
```

Or with uvicorn:

```bash
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Mode A: Route and Execute (LLM-based)

```bash
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "input": "I want to generate a new workout program",
    "user_id": "user-123",
    "context": {
      "conversation_history": [
        {"role": "user", "content": "Previous message..."}
      ]
    }
  }'
```

The router uses LLM-based intent classification for intelligent, context-aware routing. See [LLM_ROUTER_GUIDE.md](LLM_ROUTER_GUIDE.md) for details.

#### Mode B: Direct Execute

```bash
curl -X POST http://localhost:8000/api/v1/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_key": "generate_program",
    "input": "Create a hypertrophy program",
    "user_id": "user-123",
    "context": {...}
  }'
```

#### List Available Prompts

```bash
curl http://localhost:8000/api/v1/prompts
```

#### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_router.py

# Run with coverage
pytest --cov=src tests/
```

### AWS Lambda Deployment

The Lambda handler is in `src/consumer/lambda_handler.py`.

**Sample SQS Message:**

```json
{
  "job_type": "generate_program",
  "payload": {
    "user_id": "user-123",
    "program_id": "prog-456",
    "context": {
      "user_profile": {...},
      "job_context": {...},
      "available_context": {...},
      "current_routines": [...]
    },
    "input": "Generate a new program"
  }
}
```

## Prompt System

### Adding New Prompts

1. Create a new YAML file in `prompts/` (e.g., `prompts/my_new_prompt.yaml`)
2. The prompt key is automatically the filename (without extension)
3. No code changes needed - the system auto-discovers new prompts

### Prompt YAML Structure

```yaml
version: 0.1.0
prompt_type: my_new_prompt

tools:
  - name: tool_name
    description: Tool description
    parameters:
      type: object
      properties:
        param1:
          type: string

variables:
  - name: variable_name
    description: Variable description
    schema:
      type: object
      properties: {...}

role: |
  You are an AI assistant...

instruction: |
  Follow these steps...

response_type: JSON
response_schema:
  type: object
  required: [field1]
  properties:
    field1:
      type: string
```

## Configuration

All configuration is in `src/config/baseconfig.py` and loaded from environment variables.

Key settings:
- **LLM**: Model, temperature, max tokens
- **Qdrant**: URL, API key, collections, search parameters
- **Express**: Base URL, auth, timeouts, retries
- **Agent**: Max iterations, parsing retries, timeouts
- **Observability**: Log level, LangSmith tracing

## Action Router Rules

The router evaluates inputs in order:

1. **Generate Program Rule**: Keywords like "generate program", "new block", "mesocycle", "create routine"
2. **Update Routine Rule**: Keywords like "update", "modify", "tweak", exercise-specific changes
3. **Scoring Fallback**: If multiple rules match, prefer tool-requiring prompts when input references data (1RM, percentages, performance records)
4. **Default**: Falls back to `chat_response`

## Validation

All LLM outputs are validated against Pydantic schemas:

- **chat_response**: `ChatResponse` schema
- **generate_program**: `GenerateProgramResponse` schema
- **update_routine**: `UpdateRoutineResponse` schema

Domain validators ensure:
- Exercise codes exist in `available_context`
- Set type codes are valid
- Required fields are present

## Observability

### Logging

Logs are written to:
- stdout (colored, formatted)
- `logs/reppy_YYYY-MM-DD.log` (rotated daily, 7-day retention)

### LangSmith Tracing

Enable in `.env`:
```
ENABLE_LANGSMITH=true
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=reppy-rag
```

### Callback Handler

Custom `ReppyCallbackHandler` tracks:
- Tool calls (name, input, output)
- LLM calls (prompts, generations)
- Errors and timing

## Development

### Adding New Tools

1. Define input schema in `src/common/tools.py`
2. Implement tool function (async)
3. Create `StructuredTool` in `ReppyTools` class
4. Add to `get_tools_for_prompt` method

### Adding New Validation Schemas

1. Create Pydantic model in `src/common/validation.py`
2. Add to `validate_response` function
3. Optionally add domain-specific validators

## License

MIT License

## Contributors

Built with ❤️ by the Reppy team.

