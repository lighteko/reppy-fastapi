# Reppy FastAPI - RAG Pipeline with LangChain

Production-ready RAG pipeline for Reppy AI fitness coaching using LangChain, AgentExecutor, and LCEL.

## 🚀 Quick Start

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env with your API keys

# Run the server
python src/app.py
```

**Test it:**
```bash
curl http://localhost:8000/api/v1/health
```

📚 **For detailed setup, examples, and development guide, see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)**

## ✨ Features

### Core Architecture
- **🔀 Dual Execution Modes**
  - **Mode A**: Automatic LLM-based routing to appropriate prompts
  - **Mode B**: Direct execution with specified prompt
  
- **📝 Dynamic Prompt System**
  - YAML-based prompts auto-discovered from `prompts/` directory
  - Three default prompts: `chat_response`, `generate_program`, `update_routine`
  - Extensible without code changes

- **🤖 LangChain Integration**
  - Tool-calling agents with structured tools
  - LCEL pipelines with preprocessing, validation, and postprocessing
  - AgentExecutor with configurable iterations and timeouts

- **🔍 RAG Components**
  - Qdrant vector database for exercise search and user memory
  - OpenAI embeddings for semantic search
  - MMR support for diversity (configurable)

### Domain Tools
- `calculate_one_rep_max`: Calculate 1RM from workout history
- `get_exercise_details`: Fetch exercise information
- `get_exercise_performance_records`: Get user's performance history
- `recall_user_memory`: Search user's long-term memory
- `find_relevant_exercises`: Semantic exercise search
- `get_active_routines`: Fetch user's current workout routines

### Production Ready
- ✅ FastAPI with async support
- ✅ Pydantic v2 schemas for validation
- ✅ AWS Lambda consumer for SQS job processing
- ✅ Health checks for all dependencies
- ✅ Loguru-based logging with rotation
- ✅ Optional LangSmith tracing
- ✅ Comprehensive test suite

## 🏗️ Architecture

### Modular Structure

```
src/
├── common/
│   ├── agents/              # Agent building & execution
│   ├── pipeline/            # LCEL pipeline & routing
│   ├── tools/               # Tool implementations & RAG
│   └── utils/               # Prompts, validation, observability
├── api/                     # FastAPI routers
├── infra/                   # External clients (Qdrant, Express)
├── config/                  # Configuration management
└── consumer/                # AWS Lambda handler
```

### Request Flow

```
HTTP Request
    ↓
FastAPI Router
    ↓
[Mode A: Router] → LLM Classification → Prompt Selection
[Mode B: Direct] → Specified Prompt
    ↓
LCEL Pipeline
    ├── Preprocess: Format context variables
    ├── Agent: LLM + Tools execution
    ├── Parse: Extract JSON from output
    ├── Validate: Schema + domain validation
    └── Postprocess: Attach metadata
    ↓
JSON Response
```

## 🔌 API Endpoints

### Health Check
```bash
GET /api/v1/health
```

### Mode A: Route and Execute
```bash
POST /api/v1/route
Content-Type: application/json

{
  "input": "Generate a 3-day workout split for hypertrophy",
  "user_id": "user-123",
  "context": {
    "user_profile": {
      "goal": "HYPERTROPHY",
      "experience_level": "INTERMEDIATE"
    }
  }
}
```

### Mode B: Direct Execute
```bash
POST /api/v1/run
Content-Type: application/json

{
  "prompt_key": "chat_response",
  "input": "What's a good alternative to bench press?",
  "user_id": "user-123",
  "context": {
    "conversation_history": [
      {"role": "user", "content": "What's a good alternative to bench press?"}
    ]
  }
}
```

### List Available Prompts
```bash
GET /api/v1/prompts
```

## 📦 Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-api-key

# Optional
EXPRESS_BASE_URL=http://localhost:3000
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.7
AGENT_MAX_ITERATIONS=8
LOG_LEVEL=INFO
LANGSMITH_TRACING=false
```

See `env.example` for all configuration options.

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src tests/

# Run examples
python examples/test_basic.py      # No external dependencies
python examples/usage_example.py   # Requires API keys
```

## 📚 Documentation

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Development, examples, architecture deep dive
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide

## 🛠️ Technology Stack

- **Framework**: FastAPI 0.115+
- **AI**: LangChain 0.3+, OpenAI GPT-4o
- **Vector DB**: Qdrant
- **Validation**: Pydantic v2
- **Logging**: Loguru
- **Testing**: Pytest
- **Deployment**: Docker, AWS Lambda

## 📄 License

Proprietary - Reppy, Inc.

## 🤝 Contributing

This is a private repository. For questions or issues, contact the development team.
