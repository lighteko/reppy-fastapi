# Developer Guide

Complete development guide for the Reppy FastAPI RAG Pipeline.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Development Setup](#development-setup)
4. [Running Examples](#running-examples)
5. [LLM Router](#llm-router)
6. [Testing](#testing)
7. [Adding New Features](#adding-new-features)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- Qdrant Cloud account (or local Qdrant)
- Express API server (optional for full functionality)

### Installation

```bash
# Clone and navigate
cd reppy-fastapi

# Create virtual environment
python -m venv .venv

# Activate
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env with your keys
OPENAI_API_KEY=sk-your-key
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-api-key
EXPRESS_BASE_URL=http://localhost:3000
```

### Run the Server

```bash
python src/app.py
# or
uvicorn src.app:app --reload
```

Test: `curl http://localhost:8000/api/v1/health`

---

## Architecture

### Modular Structure

```
src/
├── common/
│   ├── agents/              # Agent building & execution
│   │   ├── builder.py       # Create tool-calling agents
│   │   └── executor.py      # AgentExecutor with retries
│   ├── pipeline/            # Pipeline orchestration
│   │   ├── lcel.py          # LCEL pipeline assembly
│   │   └── router.py        # LLM-based routing
│   ├── tools/               # Tool implementations
│   │   ├── implementations.py  # Domain tools
│   │   └── retriever.py        # RAG retriever
│   └── utils/               # Utilities
│       ├── prompts.py       # YAML prompt loading
│       ├── validation.py    # Response validation
│       └── observability.py # Logging & tracing
├── api/                     # FastAPI routers
├── infra/                   # External clients
├── config/                  # Configuration
└── consumer/                # AWS Lambda handler
```

### Request Flow

```
HTTP Request
    ↓
FastAPI Router
    ↓
[Mode A] → LLM Router → Intent Classification → Prompt Selection
[Mode B] → Direct Prompt Specification
    ↓
LCEL Pipeline
    ├── Preprocess: Format context variables from YAML
    ├── Agent: LLM + Tools execution (via AgentExecutor)
    ├── Parse: Extract JSON from LLM output
    ├── Validate: Schema + domain validation
    └── Postprocess: Attach metadata & citations
    ↓
JSON Response
```

### Key Design Principles

1. **No Direct Database Access**: All relational data access via Express API
2. **YAML-Based Prompts**: All prompts loaded from external YAML files
3. **Dual Modes**: Auto-routing (Mode A) and direct execution (Mode B)
4. **Modular Components**: Clean separation of concerns
5. **Comprehensive Validation**: Schema + domain guards

---

## Development Setup

### Full Local Environment

#### 1. Qdrant Setup

**Option A: Qdrant Cloud (Recommended)**
```bash
# Configure in .env
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-api-key
```

**Option B: Local Qdrant**
```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant:latest

# Configure in .env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Leave empty
```

#### 2. Create Collections

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="...", api_key="...")

# Exercises collection
client.create_collection(
    collection_name="exercises",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# User memory collection
client.create_collection(
    collection_name="user_memory",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)
```

#### 3. Express API (Optional)

For full functionality, run the Express backend:
```bash
# In your Express project
npm start
```

Update `.env`:
```bash
EXPRESS_BASE_URL=http://localhost:3000
```

### Development Tools

```bash
# Run with auto-reload
uvicorn src.app:app --reload

# Format code
black src/ tests/

# Type checking
mypy src/

# Lint
flake8 src/
```

---

## Running Examples

### Level 1: Basic Tests (No External Dependencies)

Test setup without requiring Qdrant, Express, or LLM calls:

```bash
python examples/test_basic.py
```

**Tests:**
- ✅ Module imports
- ✅ Configuration loading
- ✅ Prompt system discovery
- ✅ Router decisions

**Expected Output:**
```
[PASS] - Imports
[PASS] - Configuration
[PASS] - Prompts
[PASS] - Router
Total: 4/4 tests passed
```

### Level 2: Component Usage Examples

```bash
python examples/usage_example.py
```

**Demonstrates:**
- Listing available prompts
- Router analysis for various inputs
- Component initialization patterns
- Health check patterns

### Level 3: API Client Examples

**Terminal 1** - Start server:
```bash
python src/app.py
```

**Terminal 2** - Run examples:
```bash
python examples/api_client_example.py
```

**Tests:**
- List prompts via `/api/v1/prompts`
- Health check via `/api/v1/health`
- Mode A/B execution (if configured)

### Full Example with LLM Execution

For complete execution (requires all services):

1. **Configure .env** with all API keys
2. **Setup Qdrant** with data
3. **Start Express API**
4. **Uncomment execution lines** in examples
5. **Run:** `python examples/usage_example.py`

---

## LLM Router

### Overview

The LLM-based router uses GPT models to intelligently classify user intents and route to appropriate prompts.

### Architecture

```
User Input + Conversation History
    ↓
LLM Classification (GPT-4o-mini)
    ↓
Intent: GENERATE_ROUTINE | UPDATE_ROUTINE | CHAT_RESPONSE
    ↓
Prompt Key: generate_program | update_routine | chat_response
```

### Configuration

**Router Prompt** (`prompts/action_routing.yaml`):

```yaml
version: 0.1.0
prompt_type: intent_routing

variables:
  - name: conversation_history
    description: "Recent conversation history"

role: |
  You are an expert intent classifier for a fitness AI.

instruction: |
  Review the conversation:
  {conversation_history_json}
  
  Classify as:
  - GENERATE_ROUTINE: Creating new programs
  - UPDATE_ROUTINE: Modifying existing routines  
  - CHAT_RESPONSE: General conversation
  
  Return JSON: {"intent": "INTENT_NAME"}

response_schema:
  type: object
  required: [intent]
  properties:
    intent:
      type: string
      enum: ["GENERATE_ROUTINE", "UPDATE_ROUTINE", "CHAT_RESPONSE"]
```

### Usage

**Python SDK:**
```python
from src.common import route_input_llm

# Simple routing
prompt_key, metadata = await route_input_llm(
    "I want to create a 3-day workout split"
)
# prompt_key: "generate_program"
# metadata: {"intent": "GENERATE_ROUTINE", "method": "llm_classification"}

# With conversation history
context = {
    "conversation_history": [
        {"role": "user", "content": "What's a good chest exercise?"},
        {"role": "assistant", "content": "Bench press is excellent."},
        {"role": "user", "content": "Add that to my routine"}
    ]
}
prompt_key, metadata = await route_input_llm(
    "Add that to my routine",
    context=context
)
# prompt_key: "update_routine"
```

**API:**
```bash
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Create a strength program",
    "user_id": "user123"
  }'
```

### Pattern vs LLM Router

| Feature | Pattern Router | LLM Router |
|---------|---------------|------------|
| Accuracy | ~70-80% | ~90%+ |
| Context Awareness | Limited | Excellent |
| Latency | <1ms | ~500-1500ms |
| Cost | Free | ~$0.0001/request |
| Maintenance | Regex updates | Prompt tuning |

**Use LLM Router when:**
- Accuracy > latency
- Conversational inputs
- Context is important
- Minimize maintenance

---

## Testing

### Unit Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_llm_router.py -v

# With coverage
pytest --cov=src tests/

# Coverage report
pytest --cov=src --cov-report=html tests/
```

### Integration Tests

```bash
# LLM Router (real API calls)
python examples/test_router.py

# Full pipeline
python examples/usage_example.py
```

### Manual API Testing

```bash
# Health check
curl http://localhost:8000/api/v1/health

# List prompts
curl http://localhost:8000/api/v1/prompts

# Mode A: Auto-route
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{"input": "Generate a workout", "user_id": "test"}'

# Mode B: Direct execute
curl -X POST http://localhost:8000/api/v1/run \
  -H "Content-Type: application/json" \
  -d '{"prompt_key": "chat_response", "input": "What is bench press?", "user_id": "test"}'
```

---

## Adding New Features

### Adding a New Prompt

1. **Create YAML file** `prompts/my_new_prompt.yaml`:

```yaml
version: 0.1.0
prompt_type: my_new_prompt

tools:
  - name: my_tool
    description: "Tool description"
    parameters:
      type: object
      properties:
        param1:
          type: string

variables:
  - name: user_context
    description: "User context data"

role: |
  You are an AI assistant specialized in...

instruction: |
  Given user context:
  {user_context_json}
  
  Perform the following task...

response_type: JSON
response_schema:
  type: object
  properties:
    result:
      type: string
```

2. **Prompt automatically discovered** - no code changes needed!

3. **Test it:**
```bash
curl http://localhost:8000/api/v1/prompts
# Should include "my_new_prompt"

curl -X POST http://localhost:8000/api/v1/run \
  -d '{"prompt_key": "my_new_prompt", ...}'
```

### Adding a New Tool

1. **Define tool in `src/common/tools/implementations.py`:**

```python
class MyToolInput(BaseModel):
    param: str = Field(description="Parameter description")

def create_my_tool(client: SomeClient) -> StructuredTool:
    def run_my_tool(param: str) -> str:
        # Tool logic
        result = client.do_something(param)
        return json.dumps(result)
    
    return StructuredTool(
        name="my_tool",
        description="Tool description",
        func=run_my_tool,
        args_schema=MyToolInput,
    )
```

2. **Register in `ReppyTools.get_tools_for_prompt()`**

3. **Reference in prompt YAML** (see above)

### Adding a New Router Intent

1. **Update `prompts/action_routing.yaml`:**

```yaml
instruction: |
  Classify as:
  - GENERATE_ROUTINE
  - UPDATE_ROUTINE
  - MY_NEW_INTENT  # NEW
  - CHAT_RESPONSE

response_schema:
  properties:
    intent:
      enum: ["GENERATE_ROUTINE", "UPDATE_ROUTINE", "MY_NEW_INTENT", "CHAT_RESPONSE"]
```

2. **Update router mapping in `src/common/pipeline/router.py`:**

```python
INTENT_TO_PROMPT = {
    "GENERATE_ROUTINE": "generate_program",
    "UPDATE_ROUTINE": "update_routine",
    "MY_NEW_INTENT": "my_new_prompt",  # NEW
    "CHAT_RESPONSE": "chat_response",
}
```

3. **Create the prompt file** (see above)

---

## Troubleshooting

### Common Issues

#### ModuleNotFoundError

**Problem:** `ModuleNotFoundError: No module named 'pydantic'`

**Solution:**
```bash
# Ensure venv is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### Connection Refused (Qdrant)

**Problem:** Can't connect to Qdrant

**Solution:**
```bash
# Check Qdrant URL in .env
cat .env | grep QDRANT_URL

# For local: verify container running
docker ps | grep qdrant

# For cloud: test connection
curl -H "api-key: YOUR_KEY" https://your-cluster.cloud.qdrant.io/collections
```

#### OpenAI API Errors

**Problem:** API key errors or rate limits

**Solution:**
```bash
# Verify key is set
cat .env | grep OPENAI_API_KEY

# Check usage at platform.openai.com

# Use cheaper model for development
LLM_MODEL=gpt-4o-mini
ROUTER_LLM_MODEL=gpt-4o-mini
```

#### Import Errors After Refactoring

**Problem:** Old import paths not working

**Solution:** Update imports to use new modular structure:

```python
# OLD (deprecated)
from src.common.action_router_llm import route_input_llm

# NEW (recommended)
from src.common import route_input_llm

# Or direct import
from src.common.pipeline import route_input_llm
```

#### Router Falls Back to chat_response

**Problem:** LLM router always defaults to chat_response

**Causes & Solutions:**
1. **Missing routing prompt**
   - Ensure `prompts/action_routing.yaml` exists
   
2. **Invalid YAML**
   - Validate YAML syntax
   
3. **API errors**
   - Check OpenAI API key and quota
   - Enable debug logging: `LOG_LEVEL=DEBUG`

### Debug Mode

Enable detailed logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Or in code
import logging
logging.getLogger("src.common").setLevel(logging.DEBUG)
```

### Check Logs

```bash
# View logs
tail -f logs/reppy_*.log

# Search for errors
grep ERROR logs/reppy_*.log
```

---

## Best Practices

### Development

1. **Always use virtual environment**
2. **Keep .env out of version control**
3. **Run tests before committing**
4. **Use type hints** for better IDE support
5. **Follow existing code structure**

### Prompts

1. **Be specific in instructions**
2. **Include examples in YAML**
3. **Test with varied inputs**
4. **Version your prompts** (`version:` field)
5. **Document expected context**

### Testing

1. **Test happy path and edge cases**
2. **Mock external services**
3. **Use fixtures for common setups**
4. **Test both sync and async code**
5. **Maintain >80% coverage**

### Production

1. **Enable LangSmith for observability**
2. **Monitor LLM costs**
3. **Set appropriate timeouts**
4. **Use connection pooling**
5. **Implement rate limiting**

---

## Configuration Reference

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
QDRANT_URL=https://...
QDRANT_API_KEY=...

# Optional - LLM
LLM_MODEL=gpt-4o                    # Main model
ROUTER_LLM_MODEL=gpt-4o-mini        # Router model
LLM_TEMPERATURE=0.7                 # Creativity (0-1)
LLM_MAX_TOKENS=4096                 # Max response length
LLM_TIMEOUT=60                      # Timeout in seconds

# Optional - Agent
AGENT_MAX_ITERATIONS=8              # Max tool calls
AGENT_MAX_RETRY=2                   # Parse retries
TOOL_TIMEOUT=30                     # Tool timeout

# Optional - RAG
QDRANT_GRPC=false                   # Use gRPC
RAG_TOP_K=5                         # Results to retrieve
RAG_SCORE_THRESHOLD=0.7             # Min similarity

# Optional - Observability
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
LANGSMITH_TRACING=false             # Enable LangSmith
LANGSMITH_API_KEY=...               # If tracing enabled
LANGSMITH_PROJECT=reppy-fastapi     # Project name

# Optional - Infrastructure
EXPRESS_BASE_URL=http://localhost:3000
PROMPTS_DIRECTORY=prompts
```

### Makefile Commands

```bash
make install    # Install dependencies
make test       # Run tests
make run        # Start server
make docker-up  # Docker compose up
make clean      # Clean cache files
```

---

## Resources

### Documentation
- [README.md](README.md) - Overview & quick start
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment

### Examples
- `examples/test_basic.py` - Basic tests
- `examples/usage_example.py` - SDK usage
- `examples/api_client_example.py` - API client
- `examples/test_router.py` - Router testing

### Tests
- `tests/test_llm_router.py` - Router unit tests
- `tests/test_validation.py` - Validation tests
- `tests/test_prompts.py` - Prompt system tests

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Support

For questions or issues:
1. Check this guide and other documentation
2. Review example files
3. Check logs in `logs/`
4. Contact the development team

---

Happy coding! 🚀

