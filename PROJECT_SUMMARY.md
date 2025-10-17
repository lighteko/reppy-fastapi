# Reppy FastAPI - Project Summary

## Overview

This is a **production-ready RAG pipeline** for AI-powered fitness coaching using **LangChain**, **AgentExecutor**, and **LCEL** (LangChain Expression Language). The system implements intelligent routing, tool calling, validation, and observability for generating and managing workout programs.

## Key Features Implemented

### ✅ Core Architecture

1. **Dual Execution Modes**
   - **Mode A**: Automatic routing based on input analysis (POST `/api/v1/route`)
   - **Mode B**: Direct execution with specified prompt (POST `/api/v1/run`)

2. **Dynamic Prompt System**
   - Auto-discovers YAML files from `prompts/` directory
   - Three default prompts: `chat_response`, `generate_program`, `update_routine`
   - Extensible without code changes

3. **Action Router**
   - Rule-based routing with keyword detection
   - Scoring fallback for ambiguous inputs
   - Tool preference when data references detected (1RM, percentages, etc.)

### ✅ LangChain Integration

1. **Tool-Calling Agents**
   - Built with `create_tool_calling_agent`
   - Structured tools with Pydantic schemas
   - 7 domain-specific tools implemented

2. **LCEL Pipeline**
   - **Preprocess**: Format context variables from YAML
   - **Execute**: Run agent with tools
   - **Parse**: Extract JSON from LLM output
   - **Validate**: Schema + domain validation
   - **Postprocess**: Attach metadata and citations

3. **AgentExecutor**
   - Configurable max iterations (default: 8)
   - Parsing retries (default: 2)
   - Timeout controls for LLM and tools
   - Return intermediate steps for debugging

### ✅ Tools Implemented

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `calculate_one_rep_max` | Calculate 1RM from history | `exercise_code` |
| `get_exercise_details` | Get exercise info | `exercise_code` |
| `get_exercise_performance_records` | Get user's performance history | `exercise_code` |
| `recall_user_memory` | Search user's long-term memory | `query` |
| `find_relevant_exercises` | Semantic exercise search | `query` |
| `get_active_routines` | Get current workout routines | - |
| `retrieverTool` | Qdrant vector search | `query`, `k` |

### ✅ Infrastructure

1. **Qdrant Vector DB Client**
   - HTTP and gRPC support
   - Health checks
   - Search with filters
   - Upsert and delete operations

2. **Express API Client**
   - Async HTTP client with retries
   - Exponential backoff on 5xx errors
   - No retry on 4xx errors
   - Authentication support

3. **RAG Retriever**
   - Qdrant-backed semantic search
   - OpenAI embeddings
   - MMR support for diversity
   - Metadata preservation

### ✅ Validation & Safety

1. **Pydantic V2 Schemas**
   - `ChatResponse`: For chat_response prompt
   - `GenerateProgramResponse`: For generate_program prompt
   - `UpdateRoutineResponse`: For update_routine prompt

2. **Domain Validators**
   - Exercise code validation against `available_context`
   - Set type code validation
   - Required field checks
   - Business rule enforcement

3. **Automatic Repair**
   - Retry on parsing errors
   - Validation error detection
   - Regeneration marking

### ✅ Observability

1. **Logging**
   - Loguru-based structured logging
   - File rotation (daily, 7-day retention)
   - Colored console output
   - Configurable log levels

2. **Callbacks**
   - Custom `ReppyCallbackHandler`
   - Tracks tool calls (name, input, output)
   - Tracks LLM calls (prompts, generations)
   - Error tracking with timestamps

3. **LangSmith Integration**
   - Optional tracing support
   - Configurable project name
   - Full pipeline visibility

### ✅ API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/route` | POST | Mode A: Route and execute |
| `/api/v1/run` | POST | Mode B: Direct execute |
| `/api/v1/prompts` | GET | List available prompts |
| `/api/v1/health` | GET | Health check |
| `/` | GET | Root info |

### ✅ AWS Lambda Support

1. **Lambda Handler**
   - SQS event processing
   - Batch failure handling
   - Job types: `generate_program`, `update_routine`
   - Automatic routine saving via Express API

2. **Docker Image**
   - Lambda-compatible base image
   - Optimized for cold starts
   - Environment variable configuration

### ✅ Testing

1. **Test Coverage**
   - Prompt loader tests
   - Router decision tests
   - Qdrant client tests (mocked)
   - Express client tests (mocked)
   - Validation schema tests
   - Retriever tests (mocked)

2. **Test Tools**
   - pytest with asyncio support
   - pytest-cov for coverage
   - pytest-mock for mocking
   - Markers for unit/integration tests

## Project Structure

```
reppy-fastapi/
├── src/
│   ├── config/              # Configuration singleton
│   │   ├── baseconfig.py    # ENV-based config with Pydantic
│   │   └── __init__.py
│   ├── infra/               # Infrastructure clients
│   │   ├── qdrant_client.py # Qdrant vector DB client
│   │   ├── express_client.py# Express HTTP client with retries
│   │   └── __init__.py
│   ├── common/              # Core RAG components
│   │   ├── prompts.py       # Dynamic YAML loader with caching
│   │   ├── rag_retriever.py # Qdrant-backed retriever
│   │   ├── tools.py         # LangChain StructuredTool wrappers
│   │   ├── validation.py    # Pydantic schemas + domain guards
│   │   ├── observability.py # Logging, callbacks, tracing
│   │   ├── lcel_pipeline.py # LCEL assembly
│   │   ├── agent_builder.py # Agent construction
│   │   ├── executor.py      # AgentExecutor wrapper
│   │   ├── action_router.py # Input routing logic
│   │   └── __init__.py
│   ├── api/                 # FastAPI endpoints
│   │   ├── routers.py       # Mode A/B endpoints
│   │   └── __init__.py
│   ├── consumer/            # AWS Lambda handler
│   │   ├── lambda_handler.py# SQS message processor
│   │   └── __init__.py
│   └── app.py               # FastAPI app initialization
├── prompts/                 # YAML prompt files
│   ├── chat_response.yaml   # Chat prompt with memory tools
│   ├── generate_program.yaml# Program generation with 1RM tools
│   └── update_routine.yaml  # Routine update with performance tools
├── tests/                   # Comprehensive test suite
│   ├── test_prompts.py
│   ├── test_router.py
│   ├── test_qdrant_client.py
│   ├── test_express_client.py
│   ├── test_validation.py
│   ├── test_retriever.py
│   └── __init__.py
├── examples/                # Usage examples
│   ├── usage_example.py     # Python API usage
│   └── api_client_example.py# HTTP client usage
├── requirements.txt         # Python dependencies
├── pytest.ini               # Pytest configuration
├── env.example              # Environment template
├── Dockerfile               # Lambda deployment
├── Dockerfile.dev           # Development image
├── docker-compose.yml       # Local development stack
├── Makefile                 # Common commands
├── README.md                # Main documentation
├── DEPLOYMENT.md            # Deployment guide
└── PROJECT_SUMMARY.md       # This file
```

## Configuration

All configuration via environment variables (see `env.example`):

### Required
- `OPENAI_API_KEY`: OpenAI API key
- `QDRANT_URL`: Qdrant server URL
- `EXPRESS_BASE_URL`: Express API base URL

### Optional (with defaults)
- `LLM_MODEL`: gpt-4-turbo-preview
- `LLM_TEMPERATURE`: 0.7
- `AGENT_MAX_ITERATIONS`: 8
- `TOOL_TIMEOUT`: 30s
- `LOG_LEVEL`: INFO

## Quick Start

### Local Development

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Edit .env

# Run
python src/app.py

# Test
pytest
```

### Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop
docker-compose down
```

### AWS Lambda

```bash
# Build and push
docker build -f Dockerfile -t reppy-lambda .
docker tag reppy-lambda <ecr-url>
docker push <ecr-url>

# Create function
aws lambda create-function \
  --function-name reppy-rag \
  --package-type Image \
  --code ImageUri=<ecr-url> \
  ...
```

## Action Router Logic

### Evaluation Order

1. **Rule 1: Generate Program**
   - Keywords: "generate program", "new block", "mesocycle", "create routine"
   - → Routes to `generate_program`

2. **Rule 2: Update Routine**
   - Keywords: "update", "modify", "tweak", "progress", exercise deltas
   - → Routes to `update_routine`

3. **Rule 3: Scoring Fallback**
   - Calculate scores for each prompt
   - Boost tool-using prompts if data references detected
   - → Routes to highest score

4. **Default**
   - → Routes to `chat_response`

### Data Reference Detection

If input contains:
- "1rm", "one rep max"
- "percentage", "%"
- "performance", "records"
- "last workout", "progress"
- "schedule", "date"

→ Boosts scores for `generate_program` and `update_routine`

## Validation Flow

1. **Schema Validation**
   - Parse LLM output as JSON
   - Validate against Pydantic schema for prompt type
   - Check required fields

2. **Domain Validation**
   - Verify exercise codes exist in `available_context`
   - Verify set type codes are valid
   - Check business rules (e.g., routine order uniqueness)

3. **Repair/Regeneration**
   - On validation failure, mark for regeneration
   - Return errors and warnings
   - Client can retry with adjustments

## Extension Points

### Adding New Prompts

1. Create `prompts/new_prompt.yaml`
2. Define tools, variables, role, instruction, response schema
3. System auto-discovers on startup
4. Optionally add routing rules in `action_router.py`

### Adding New Tools

1. Define input schema in `tools.py`
2. Implement async function
3. Create `StructuredTool` in `ReppyTools`
4. Add to `get_tools_for_prompt` mapping

### Adding New Validation

1. Define Pydantic model in `validation.py`
2. Add to `validate_response` function
3. Optionally add domain validators

## Performance Considerations

### Latency

- **Cold start**: ~3-5s (Lambda)
- **Warm execution**: ~2-10s (depends on tool calls)
- **LLM call**: ~1-5s per call
- **Tool call**: ~100-500ms per call

### Cost Optimization

1. **Reduce max_iterations**: Lower = fewer LLM calls
2. **Cache embeddings**: Reduce OpenAI embedding API calls
3. **Batch tool calls**: Reduce Express API calls
4. **Lower k**: Fewer vector search results

### Scaling

1. **Horizontal**: Multiple Lambda/FastAPI instances
2. **Vertical**: Increase Lambda memory, use larger instance
3. **Caching**: Redis for prompt/embedding cache
4. **Queue**: SQS for async job processing

## Monitoring Recommendations

1. **CloudWatch Metrics**
   - Lambda invocations, errors, duration
   - API Gateway requests, latency
   - SQS queue depth, processing time

2. **Application Metrics**
   - Tool call frequency and latency
   - Validation failure rate
   - Prompt usage distribution

3. **LangSmith**
   - Full trace visibility
   - Tool output inspection
   - Error debugging

## Known Limitations

1. **Streaming**: Not yet implemented for Mode A/B
2. **MMR**: Basic implementation, not fully optimized
3. **Reranking**: Placeholder, not implemented
4. **Tool Retry**: No automatic retry on tool failures
5. **Context Window**: Limited by LLM max tokens (4K default)

## Future Enhancements

1. **Streaming Responses**: SSE for real-time output
2. **Caching Layer**: Redis for prompts, embeddings, tool results
3. **Advanced MMR**: Full diversity scoring implementation
4. **Reranking**: Cohere or similar for result refinement
5. **Multi-modal**: Image/video exercise demonstrations
6. **Fine-tuning**: Custom models for program generation
7. **A/B Testing**: Router decision analysis
8. **Prompt Versioning**: Track changes, rollback support

## Dependencies

### Core
- `fastapi==0.116.1`: Web framework
- `langchain==0.3.26`: LLM orchestration
- `langchain-openai==0.3.28`: OpenAI integration
- `langchain-qdrant==0.2.0`: Qdrant integration
- `pydantic==2.11.7`: Data validation
- `pydantic-settings==2.10.1`: Config management

### Infrastructure
- `qdrant-client==1.14.3`: Vector database
- `httpx==0.28.1`: HTTP client
- `tenacity==9.1.2`: Retry logic
- `boto3==1.35.93`: AWS SDK

### Observability
- `loguru==0.7.3`: Logging
- `langsmith==0.4.6`: Tracing (optional)

### Testing
- `pytest==8.0.0`: Test framework
- `pytest-asyncio==0.23.5`: Async test support
- `pytest-cov==4.1.0`: Coverage reporting

## Documentation

- **README.md**: Main documentation
- **DEPLOYMENT.md**: Deployment guide
- **PROJECT_SUMMARY.md**: This file
- **examples/**: Usage examples
- **tests/**: Test examples

## Support

For questions or issues:
1. Check README.md for usage
2. Review DEPLOYMENT.md for setup
3. Check examples/ for code samples
4. Review tests/ for patterns
5. Open GitHub issue

---

**Status**: ✅ Production Ready

**Version**: 1.0.0

**Last Updated**: 2025-10-17

**Authors**: Reppy Development Team

