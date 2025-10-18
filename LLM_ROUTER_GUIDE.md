# LLM-Based Action Router Guide

## Overview

The **LLM-Based Action Router** uses a language model to intelligently classify user intents and route them to the appropriate prompt handler. Unlike pattern-matching routers, this approach leverages the LLM's natural language understanding to make more contextually aware routing decisions.

## Architecture

```
User Input
    ↓
Conversation History (optional)
    ↓
LLM Classification
    ↓
Intent: GENERATE_ROUTINE | UPDATE_ROUTINE | CHAT_RESPONSE
    ↓
Prompt Key: generate_program | update_routine | chat_response
```

## Key Features

1. **Context-Aware**: Can use conversation history to understand ambiguous requests
2. **Natural Language Understanding**: Better handles variations and edge cases
3. **Zero Code Changes**: Add new routing intents via YAML prompts only
4. **Fallback Support**: Gracefully falls back to `chat_response` on errors
5. **Observable**: Logs routing decisions with confidence metadata

## Configuration

### 1. Routing Prompt (YAML)

The router uses `prompts/action_routing.yaml` to define the classification logic:

```yaml
version: 0.1.0
prompt_type: intent_routing

# No tools needed for classification
tools: []

# Variables for context
variables:
  - name: conversation_history
    description: "Recent conversation history"
    schema:
      type: array
      items:
        type: object

# System role
role: |
  You are an expert intent classification router. Analyze the user's 
  message and determine which prompt should handle it.

# Classification instructions
instruction: |
  Review the conversation history:
  {conversation_history_json}
  
  Classify the intent as one of:
  - GENERATE_ROUTINE: Creating new workout programs
  - UPDATE_ROUTINE: Modifying existing routines
  - CHAT_RESPONSE: All other conversations
  
  Return JSON: {"intent": "INTENT_NAME"}

# Response schema
response_type: JSON
response_schema:
  type: object
  required: [intent]
  properties:
    intent:
      type: string
      enum: ["GENERATE_ROUTINE", "UPDATE_ROUTINE", "CHAT_RESPONSE"]
```

### 2. Intent to Prompt Mapping

The router maps LLM intents to prompt keys:

```python
INTENT_TO_PROMPT = {
    "GENERATE_ROUTINE": "generate_program",
    "UPDATE_ROUTINE": "update_routine",
    "CHAT_RESPONSE": "chat_response",
}
```

## Usage

### Basic Usage (Mode A with LLM Router)

```python
from src.common.action_router_llm import route_input_llm

# Simple routing
prompt_key, metadata = await route_input_llm(
    "I want to create a new 3-day workout split"
)

print(f"Route to: {prompt_key}")  # "generate_program"
print(f"Intent: {metadata['intent']}")  # "GENERATE_ROUTINE"
```

### With Conversation History

```python
context = {
    "conversation_history": [
        {"role": "user", "content": "What's a good chest exercise?"},
        {"role": "assistant", "content": "Bench press is excellent."},
        {"role": "user", "content": "Can you add that to my routine?"},
    ]
}

prompt_key, metadata = await route_input_llm(
    "Can you add that to my routine?",
    context=context
)

print(f"Route to: {prompt_key}")  # "update_routine"
```

### API Usage

Enable LLM routing via the API by setting `use_llm_router=true`:

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{
    "input": "I want a new workout program for strength",
    "user_id": "user123",
    "use_llm_router": true
  }'
```

Response includes routing metadata:

```json
{
  "result": "...",
  "prompt_key": "generate_program",
  "metadata": {
    "routing_method": "llm",
    "routing_info": {
      "method": "llm_classification",
      "intent": "GENERATE_ROUTINE",
      "prompt_key": "generate_program"
    }
  }
}
```

### Python SDK Example

```python
import asyncio
from src.common.action_router_llm import LLMActionRouter

async def main():
    # Initialize router (uses config from .env)
    router = LLMActionRouter()
    
    # Test various inputs
    test_cases = [
        "Create a new 3-day program",           # GENERATE_ROUTINE
        "Make my push day harder",              # UPDATE_ROUTINE
        "What's a good chest exercise?",        # CHAT_RESPONSE
    ]
    
    for user_input in test_cases:
        prompt_key, metadata = await router.route(user_input)
        print(f"Input: {user_input}")
        print(f"  → {prompt_key} ({metadata['intent']})\n")

asyncio.run(main())
```

## Comparison: Pattern vs LLM Router

| Feature | Pattern Router | LLM Router |
|---------|---------------|------------|
| **Accuracy** | ~70-80% | ~90%+ |
| **Context Awareness** | Limited | Excellent |
| **Setup Complexity** | Low | Medium |
| **Latency** | <1ms | ~500-1500ms |
| **Cost** | Free | ~$0.0001/request |
| **Maintenance** | Regex updates | Prompt tuning |

### When to Use LLM Router

✅ **Use LLM Router when:**
- Accuracy is more important than latency
- User inputs are varied and conversational
- Context from conversation history is important
- You want to minimize pattern maintenance

❌ **Use Pattern Router when:**
- Sub-second response times are critical
- Inputs follow predictable patterns
- Cost optimization is a priority
- You want deterministic behavior

## Advanced Features

### Custom LLM Configuration

```python
from langchain_openai import ChatOpenAI
from src.common.action_router_llm import LLMActionRouter

# Use a different model for routing
routing_llm = ChatOpenAI(
    model="gpt-4o-mini",  # Faster, cheaper
    temperature=0.0,       # Deterministic
    max_tokens=50,         # Short responses
)

router = LLMActionRouter(llm=routing_llm)
```

### Extending with New Intents

To add a new intent (e.g., `SCHEDULE_WORKOUT`):

1. **Update `action_routing.yaml`**:

```yaml
instruction: |
  Classify the intent as one of:
  - GENERATE_ROUTINE
  - UPDATE_ROUTINE
  - SCHEDULE_WORKOUT  # NEW
  - CHAT_RESPONSE

response_schema:
  properties:
    intent:
      enum: ["GENERATE_ROUTINE", "UPDATE_ROUTINE", "SCHEDULE_WORKOUT", "CHAT_RESPONSE"]
```

2. **Update the router mapping**:

```python
INTENT_TO_PROMPT = {
    "GENERATE_ROUTINE": "generate_program",
    "UPDATE_ROUTINE": "update_routine",
    "SCHEDULE_WORKOUT": "schedule_workout",  # NEW
    "CHAT_RESPONSE": "chat_response",
}
```

3. **Create the prompt file**: `prompts/schedule_workout.yaml`

That's it! No other code changes required.

### Fallback Handling

The router includes multiple fallback layers:

```python
# Layer 1: No routing prompt found
if self.routing_prompt is None:
    return "chat_response", {"method": "fallback"}

# Layer 2: LLM call fails
except Exception as e:
    logger.error(f"LLM routing failed: {e}")
    return "chat_response", {"method": "error_fallback"}

# Layer 3: Invalid intent parsed
if intent not in self.INTENT_TO_PROMPT:
    logger.warning(f"Invalid intent '{intent}'")
    return "CHAT_RESPONSE"  # Safe default
```

## Testing

Run the test suite:

```bash
# Unit tests (mocked LLM)
pytest tests/test_llm_router.py -v

# Integration tests (real LLM calls)
python examples/test_llm_router.py
```

## Monitoring & Observability

The router logs all decisions:

```
[INFO] LLM classified intent as: GENERATE_ROUTINE -> generate_program
```

Metadata includes:

```python
{
    "method": "llm_classification",
    "intent": "GENERATE_ROUTINE",
    "prompt_key": "generate_program",
    "llm_response": "{'intent': 'GENERATE_ROUTINE'}"  # truncated
}
```

## Troubleshooting

### Common Issues

**1. Router falls back to `chat_response` for everything**

- **Cause**: `action_routing.yaml` not found or invalid
- **Fix**: Ensure `prompts/action_routing.yaml` exists and is valid YAML

**2. LLM routing fails with API errors**

- **Cause**: Invalid API key or quota exceeded
- **Fix**: Check `OPENAI_API_KEY` in `.env` and API usage

**3. Incorrect classifications**

- **Cause**: Prompt instructions unclear
- **Fix**: Improve examples in `action_routing.yaml`

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("src.common.action_router_llm").setLevel(logging.DEBUG)
```

## Performance Optimization

### 1. Use Faster Models

```python
# Use GPT-4o-mini for routing (cheaper, faster)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=50)
```

### 2. Cache Results

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def route_cached(input_text: str) -> str:
    return asyncio.run(route_input_llm(input_text))
```

### 3. Batch Routing

For bulk operations, batch multiple classifications:

```python
tasks = [router.route(input_text) for input_text in inputs]
results = await asyncio.gather(*tasks)
```

## Migration from Pattern Router

To migrate existing code:

```python
# Before (pattern router)
from src.common.action_router import route_input
prompt_key, scores = route_input(user_input)

# After (LLM router)
from src.common.action_router_llm import route_input_llm
prompt_key, metadata = await route_input_llm(user_input)
```

Or use both with a flag:

```python
if use_llm:
    prompt_key, info = await route_input_llm(user_input)
else:
    prompt_key, info = route_input(user_input)
```

## Best Practices

1. **Always provide conversation history** for ambiguous requests
2. **Use temperature=0** for consistent routing
3. **Log routing decisions** for monitoring and debugging
4. **Test edge cases** with real user inputs
5. **Monitor LLM costs** if routing high volumes
6. **Keep instructions clear** in the routing prompt
7. **Use fallback gracefully** when LLM fails

## Examples

See working examples in:
- `examples/test_llm_router.py` - Full test suite with real LLM calls
- `tests/test_llm_router.py` - Unit tests with mocked LLM
- `src/api/routers.py` - API integration

## Summary

The LLM-based router provides intelligent, context-aware routing with minimal configuration. It's ideal for production systems where accuracy and user experience are prioritized over ultra-low latency.

**Next Steps:**
1. Review `prompts/action_routing.yaml`
2. Run `python examples/test_llm_router.py`
3. Enable in API with `use_llm_router=true`
4. Monitor performance and adjust as needed

