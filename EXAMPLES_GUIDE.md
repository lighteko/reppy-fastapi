# Examples Guide

This guide shows you how to run and test the Reppy RAG pipeline examples.

## 📋 Prerequisites

1. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment configured** (optional for basic tests):
   ```bash
   cp env.example .env
   # Edit .env with your keys
   ```

## 🧪 Test Levels

### Level 1: Basic Tests (No External Dependencies)

Test that everything is set up correctly **without** requiring Qdrant, Express API, or LLM calls.

```bash
python examples/test_basic.py
```

**What it tests:**
- ✅ All modules can be imported
- ✅ Configuration loads correctly
- ✅ Prompt system discovers YAML files
- ✅ Action router makes correct routing decisions

**Output:**
```
[PASS] - Imports
[PASS] - Configuration
[PASS] - Prompts
[PASS] - Router

Total: 4/4 tests passed
```

### Level 2: Python SDK Examples (Requires Configuration)

Shows internal component usage **without** starting the server.

```bash
python examples/usage_example.py
```

**What it does:**
- Lists available prompts
- Demonstrates router decision-making
- Shows health check patterns
- **Note:** Actual LLM execution is commented out

**Output:**
```
=== List Available Prompts ===

Available prompts (3):
  - chat_response
  - generate_program
  - update_routine

=== Router Analysis ===

Input: 'Generate a new program for me'
  → Routed to: generate_program
  → Scores: {'generate_program': 1.0}
```

### Level 3: API Client Examples (Requires Server)

Test HTTP endpoints **after** starting the server.

**Terminal 1** - Start the server:
```bash
python src/app.py
```

**Terminal 2** - Run API examples:
```bash
python examples/api_client_example.py
```

**What it does:**
- ✅ Lists prompts via `/api/v1/prompts`
- ✅ Checks health via `/api/v1/health`
- ⚠️ Actual execution examples are commented out (require full setup)

## 📝 Running the Examples

### Example 1: Basic Test ✅ (Recommended First)

```bash
cd d:\Developments\Server\reppy-fastapi
python examples/test_basic.py
```

**Success Output:**
```
[SUCCESS] All tests passed! Your setup is working correctly.
```

### Example 2: Usage Demo

```bash
python examples/usage_example.py
```

**Shows:**
- How to load prompts
- How routing works
- Component initialization patterns

### Example 3: API Test

**Step 1:** Start server
```bash
python src/app.py
```

Wait for:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Step 2:** Test API (new terminal)
```bash
python examples/api_client_example.py
```

**Expected:**
```
=== List Prompts ===

Available prompts (3):
  - chat_response
  - generate_program
  - update_routine

=== Health Check ===

Overall status: healthy
```

## 🚀 Full Working Example (All Services)

For **complete** LLM execution, you need:

### Prerequisites:

1. **Environment configured** (`.env`):
   ```env
   OPENAI_API_KEY=sk-your-key
   QDRANT_URL=https://your-cluster.cloud.qdrant.io
   QDRANT_API_KEY=your-api-key
   EXPRESS_BASE_URL=http://localhost:3000
   ```

2. **Qdrant setup**:
   - See [QDRANT_SETUP.md](QDRANT_SETUP.md)
   - Collections created: `exercises`, `user_memory`
   - Data populated

3. **Express API running**:
   ```bash
   # Start your Express backend
   npm start  # or however you run it
   ```

### Running Full Example:

```bash
# Uncomment the execution lines in usage_example.py
# Then run:
python examples/usage_example.py
```

This will actually call LLMs and tools!

## 🧰 Useful Commands

### Quick Health Check

```bash
# Check if server is running
curl http://localhost:8000/api/v1/health

# List available prompts
curl http://localhost:8000/api/v1/prompts
```

### Test Individual Components

```python
# In Python REPL
from src.common.prompts import list_prompts, load_prompt

# List prompts
prompts = list_prompts()
print(prompts)

# Load a prompt
prompt = load_prompt("chat_response")
print(prompt.get("prompt_type"))
```

### Test Router

```python
from src.common.action_router import route_input

# Test routing
prompt_key, scores = route_input("Generate a workout program")
print(f"Routed to: {prompt_key}")
```

## 📊 Example Output Reference

### Basic Test Output (Success)

```
============================================================
  Reppy RAG Pipeline - Basic Tests
============================================================
Testing imports...
[OK] Config module imported
[OK] Prompts module imported
[OK] Action router imported

Testing configuration...
[OK] LLM Model: gpt-4-turbo-preview
[OK] Temperature: 0.7
[OK] OpenAI API key is set

Testing prompt system...
[OK] Found 3 prompts: ['chat_response', 'generate_program', 'update_routine']

Testing action router...
[OK] 'Generate a new workout program' -> generate_program

[SUCCESS] All tests passed!
```

### API Client Output (Server Running)

```
=== List Prompts ===

Available prompts (3):
  - chat_response
  - generate_program
  - update_routine

=== Health Check ===

Overall status: healthy

Services:
  qdrant: healthy
  express: healthy
```

## 🔧 Troubleshooting

### Issue: ModuleNotFoundError

**Problem:** `ModuleNotFoundError: No module named 'pydantic'`

**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: Unicode Encode Error

**Problem:** `UnicodeEncodeError: 'cp949' codec can't encode character`

**Solution:** Already fixed in `test_basic.py` (no emojis used)

### Issue: Connection Refused (Qdrant)

**For tests:** Basic tests don't require Qdrant - they'll still pass!

**For full execution:** Check your Qdrant URL in `.env`

### Issue: Server Not Running

**Problem:** API client can't connect

**Solution:**
```bash
# Make sure server is running
python src/app.py

# Check it's listening
curl http://localhost:8000/
```

### Issue: OpenAI API Key Not Set

**For basic tests:** Tests will show warning but still pass

**For LLM execution:** Set in `.env`:
```env
OPENAI_API_KEY=sk-your-actual-key-here
```

## 📚 Next Steps

After running the examples:

1. **Configure production settings**
   - See [DEPLOYMENT.md](DEPLOYMENT.md)

2. **Setup Qdrant with data**
   - See [QDRANT_SETUP.md](QDRANT_SETUP.md)

3. **Integrate with your Express API**
   - Update `EXPRESS_BASE_URL` in `.env`

4. **Try Mode A/B execution**
   - POST to `/api/v1/route` (Mode A)
   - POST to `/api/v1/run` (Mode B)

5. **Run tests**
   ```bash
   pytest -v
   ```

## 💡 Tips

1. **Start simple**: Run `test_basic.py` first to verify setup
2. **Check logs**: Look in `logs/reppy_*.log` for detailed output
3. **Use health endpoint**: `/api/v1/health` shows service status
4. **Test routing**: Use `/api/v1/route` without full context first
5. **Enable debug**: Set `LOG_LEVEL=DEBUG` in `.env` for more details

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Review [QUICKSTART.md](QUICKSTART.md)
3. Check [README.md](README.md) for architecture details
4. Look at test files in `tests/` for usage patterns

---

Happy testing! 🚀

