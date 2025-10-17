# Quick Start Guide

Get the Reppy RAG pipeline running in 5 minutes.

## Prerequisites

- Python 3.11+
- Git
- OpenAI API key
- **Qdrant Cloud account** (recommended) or local Qdrant
- Express API server

> 💡 **Remote Qdrant**: This guide assumes you're using Qdrant Cloud. See [QDRANT_SETUP.md](QDRANT_SETUP.md) for setup details.

## Installation

```bash
# Clone repository (if not already cloned)
cd reppy-fastapi

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env and set required variables:
# - OPENAI_API_KEY=your-openai-api-key
# - QDRANT_URL=http://localhost:6333
# - EXPRESS_BASE_URL=http://localhost:3000
```

**Minimum required configuration:**
```env
OPENAI_API_KEY=sk-your-key-here
QDRANT_URL=https://your-cluster.cloud.qdrant.io  # Or http://localhost:6333 for local
QDRANT_API_KEY=your-qdrant-api-key  # Required for Qdrant Cloud
EXPRESS_BASE_URL=http://localhost:3000
```

## Setup Qdrant

### Option 1: Remote Qdrant Cloud (Recommended)

If you're using Qdrant Cloud:

```env
# In your .env file
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-api-key-here
```

No local setup needed! Skip to "Run the Application" section.

### Option 2: Local Qdrant (Development)

If you want to run Qdrant locally:

```bash
# Using Docker
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant:latest

# Verify it's running
curl http://localhost:6333/collections

# Update .env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Leave empty for local
```

## Run the Application

```bash
# Start FastAPI server
python src/app.py

# Or with uvicorn:
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

## Test the API

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### List Available Prompts

```bash
curl http://localhost:8000/api/v1/prompts
```

### Mode A: Route and Execute

```bash
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "input": "I want to generate a new workout program",
    "user_id": "test-user-123",
    "context": {
      "user_profile": {
        "goal": "HYPERTROPHY",
        "experience_level": "INTERMEDIATE"
      }
    }
  }'
```

### Mode B: Direct Execute

```bash
curl -X POST http://localhost:8000/api/v1/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_key": "chat_response",
    "input": "What is a good chest exercise?",
    "user_id": "test-user-123",
    "context": {}
  }'
```

## Run Tests

```bash
# All tests
pytest

# With output
pytest -v

# With coverage
pytest --cov=src tests/
```

## Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Using Docker Compose (Alternative)

Start everything with Docker Compose:

```bash
# Start all services (Qdrant + API)
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop everything
docker-compose down
```

## Example Usage

### Python Client

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/route",
    json={
        "input": "Create a strength program",
        "user_id": "user-123",
        "context": {
            "user_profile": {
                "goal": "STRENGTH",
                "experience_level": "ADVANCED"
            }
        }
    }
)

result = response.json()
print(f"Success: {result['success']}")
print(f"Prompt: {result['prompt_key']}")
```

### Run Examples

```bash
# Python usage examples
python examples/usage_example.py

# API client examples
python examples/api_client_example.py
```

## Common Issues

### "Connection refused" for Qdrant

**For Remote Qdrant:**
- Check your `QDRANT_URL` is correct (should be `https://...`)
- Verify your `QDRANT_API_KEY` is set
- Test connection: `curl -H "api-key: YOUR_KEY" https://your-cluster.cloud.qdrant.io/collections`

**For Local Qdrant:**
```bash
docker ps | grep qdrant
# If not running:
docker run -d -p 6333:6333 qdrant/qdrant:latest
# Test: curl http://localhost:6333/collections
```

### "OpenAI API key not set"

**Solution**: Check your `.env` file:
```bash
cat .env | grep OPENAI_API_KEY
# Should show: OPENAI_API_KEY=sk-...
```

### Import errors

**Solution**: Make sure virtual environment is activated and dependencies installed:
```bash
which python  # Should point to .venv/bin/python
pip install -r requirements.txt
```

## Next Steps

1. **Read the main README**: Detailed architecture and features
2. **Check DEPLOYMENT.md**: Production deployment guide
3. **Review PROJECT_SUMMARY.md**: Complete feature overview
4. **Explore examples/**: Code examples and patterns
5. **Run tests**: `pytest -v` to see all test cases

## Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root info |
| `/api/v1/health` | GET | Health check |
| `/api/v1/prompts` | GET | List prompts |
| `/api/v1/route` | POST | Mode A (auto-route) |
| `/api/v1/run` | POST | Mode B (direct) |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc UI |

## Default Prompts

1. **chat_response**: Conversational AI with memory
2. **generate_program**: Generate workout programs
3. **update_routine**: Update existing routines

## Configuration Highlights

Key environment variables:

```env
# LLM
LLM_MODEL=gpt-4-turbo-preview
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# Agent
AGENT_MAX_ITERATIONS=8
TOOL_TIMEOUT=30
LLM_TIMEOUT=60

# Logging
LOG_LEVEL=INFO
```

See `env.example` for all options.

## Getting Help

- **Documentation**: Check README.md, DEPLOYMENT.md, PROJECT_SUMMARY.md
- **Examples**: See `examples/` directory
- **Tests**: See `tests/` directory for usage patterns
- **Logs**: Check `logs/reppy_*.log` files

## Quick Commands

```bash
# Install
make install

# Test
make test

# Run
make run

# Docker
make docker-up
make docker-down

# Clean
make clean
```

---

You're ready to go! 🚀

For detailed information, see [README.md](README.md).

