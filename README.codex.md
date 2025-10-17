# Reppy - AI-Powered Fitness Service

This repository contains the complete Python AI service for the Reppy fitness application.

## 🚀 LangChain Refactoring Complete

This project has been refactored to utilize **LangChain** for all AI operations. See [README.LANGCHAIN.md](README.LANGCHAIN.md) for detailed documentation on:

- LangChain Tools for function calling (`calculate_one_rep_max`, `get_exercise_details`)
- LangChain Agents with ReAct-style reasoning
- LangChain Qdrant integration for vector search
- LangChain OpenAI for streaming and structured output
- Complete 5-step workflow implementation from `generate_routine.yaml`

**New LangChain Components:**
- `src/common/langchain_tools.py` - Structured tools with Pydantic schemas
- `src/common/langchain_agent.py` - ReAct agents for complex reasoning
- `src/common/langchain_orchestrator.py` - RAG orchestration with LangChain
- `src/common/langchain_chat.py` - Streaming chat service
- `examples/langchain_usage.py` - Usage examples

## ✅ Implementation Complete

The service has been fully implemented using **LangChain** and following these critical design principles:

This service must not access the PostgreSQL database directly. All relational data (like user profiles or saving new routines) must be handled by making HTTP requests to the main Express.js API server.

The DDL of the Relational Database for Reppy is located in the root directory. Read the DDL file and reason the functionalities.

All prompts sent to the LLM must be loaded from external YAML files for easy management.

The service will have two modes of operation: a FastAPI server for real-time requests and a background worker for asynchronous jobs from AWS SQS.

1. Project Structure
   Organize the code into the following file structure:

/reppy-ai-service
|
|-- /src
| |-- /common
| | |-- **init**.py
| | |-- clients.py # Initializes Qdrant, OpenAI clients
| | |-- express_client.py # HTTP client to talk to the Express API
| | |-- models.py # Pydantic data models
| | |-- orchestrator.py # Core RAG orchestration logic
| |
| |-- api.py # FastAPI web server
| |-- worker.py # SQS background worker
|
|-- /prompts
| |-- generate_routine.yaml # Prompt template for routine generation
| |-- chat_response.yaml # Prompt template for the chatbot
|
|-- requirements.txt
|-- .env.example 2. Shared Logic (src/common)
clients.py:

Initialize singleton clients for OpenAI and QdrantClient using environment variables.

express_client.py:

Create an ExpressAPIClient class using the httpx library.

It should be configured with the base URL of the Express server from an environment variable (e.g., EXPRESS_API_URL).

Implement asynchronous methods for all necessary interactions with the RDB, such as:

async get_user_profile(user_id: str) -> dict

async get_exercises_by_ids(exercise_ids: list[str]) -> list[dict]

async save_batch_routines(routines_json: dict) -> None

orchestrator.py:

Create a RAGOrchestrator class initialized with the OpenAIClient, QdrantClient, and ExpressAPIClient.

Implement generate_routine_from_rag(user_id, user_context) which performs the RAG pipeline:

Makes an HTTP call via express_client.get_user_profile() to fetch user data.

Queries Qdrant for relevant exercise IDs.

Makes another HTTP call via express_client.get_exercises_by_ids() to "hydrate" the results.

Loads the prompt template from /prompts/generate_routine.yaml.

Formats the template with all the retrieved context.

Calls the OpenAI API to generate the routine JSON and returns it.

3. Prompt Templates (/prompts)

You should create a structured prompt using distinct keys.

The format is written below:

```YAML
version: 1.0.0
prompt:
  prompt_type: #
  tools: [] # valid functions to prevent value hallucinations.
  variables: [] # The varibles will be given by default. Reason yourself what varibles might be needed.
  role: | # Write valid role description here.
    dummy text
  instruction: | # write valid instruction on the actions what the model shoule execute.
    dummy text
  response_type: JSON
  response_schema:
    # Refer to the schema definition for Express API server.
```

You can add keys to the prompt if needed.

The schema below is how the AI-generated routine data are handled in Express API server.

```TypeScript
export const UpdateProgramSchema = z.object({
    programId: z.uuid(),
    userId: z.uuid(),
    programName: z.string().optional(),
    startDate: z.iso.datetime().optional(),
    goalDate: z.iso.datetime().optional(),
    goal: z.string().optional(),
});

const SetSchema = z.object({
    setTypeId: z.uuid(),
    setOrder: z.int(),
    reps: z.int().optional(),
    weight: z.float32().optional(),
    restTime: z.int(),
    duration: z.int().optional(),
});

const PlanSchema = z.object({
    exerciseId: z.uuid(),
    description: z.string(),
    memo: z.string().optional(),
    execOrder: z.int(),
    sets: z.array(SetSchema).min(1),
});

const RoutineSchema = z.object({
    routineName: z.string(),
    routineOrder: z.int(),
    plans: z.array(PlanSchema).min(1),
});

export const CreateBatchRoutinesSchema = z.object({
    programId: z.uuid(),
    userId: z.uuid(),
    routines: z.array(RoutineSchema).min(1),
});

export const CreateRoutineSchema = z.object({
    programId: z.uuid(),
    userId: z.uuid(),
    routineName: z.string(),
    routineOrder: z.int(),
    plans: z.array(PlanSchema).min(1),
});
```

The AI generated routines should be in form of CreateBatchRoutinesSchema. For sure, the id part won't be handled by the AI, so you should exclude them in the response schema.

4. FastAPI Server (src/api.py)
   Use FastAPI.

Create a POST /chat/stream endpoint that accepts a ChatRequest model.

It should load its prompt from /prompts/chat_response.yaml.

It will call the OpenAI API with stream: true and return a StreamingResponse.

5. SQS Worker (src/worker.py)
   Use boto3 to poll an AWS SQS queue.

When a generate_program job is received:

Instantiate the RAGOrchestrator.

Call the generate_routine_from_rag method.

Take the final generated routine JSON and call express_client.save_batch_routines() to send it to the Express server for saving.

After the Express API confirms the save, delete the message from the SQS queue.

Include robust error handling.

6. Dependencies (requirements.txt)
   Please include: fastapi, uvicorn, boto3, openai, qdrant-client, pydantic, httpx (for the Express client), and PyYAML (for loading prompts).

7. This service will be uploaded initailly as a docker container to AWS Lambda.

8. The Qdrant Collection Schema is below:

```JSON
// exercises
{
    "vectors": {
      "size": "{your_embedding_dimension}",
      "distance": "Cosine"
    },
    "payload_schema": {
      "source_id": {
        "type": "uuid",
        "indexed": true,
        "description": "The exercise_id from your PostgreSQL database. The vital link."
      },
      "name": {
        "type": "text",
        "indexed": true,
        "description": "The human-readable name, e.g., 'Barbell Squat'."
      },
      "main_muscle_id": {
        "type": "uuid",
        "indexed": true,
        "description": "UUID of the main muscle group for filtering."
      },
      "equipment_id": {
        "type": "uuid",
        "indexed": true,
        "description": "UUID of the required equipment for filtering."
      },
      "difficulty_level": {
        "type": "integer",
        "indexed": true,
        "description": "Numeric difficulty (e.g., 1 for Beginner)."
      }
    }
  }
```

```JSON
// user_memory
{
    "vectors": {
      "size": "{your_embedding_dimension}",
      "distance": "Cosine"
    },
    "payload_schema": {
      "source_id": {
        "type": "uuid",
        "indexed": true,
        "description": "The message_id or feedback_id from PostgreSQL where this memory originated."
      },
      "user_id": {
        "type": "uuid",
        "indexed": true,
        "description": "The most critical field. This scopes all memories to a specific user for personalization."
      },
      "created_at": {
        "type": "datetime",
        "indexed": true,
        "description": "Timestamp of when the memory was formed, for recalling recent information."
      },
      "memory_type": {
        "type": "keyword",
        "indexed": true,
        "description": "A category for the memory, e.g., 'goal', 'preference', 'injury_note'."
      },
      "content": {
        "type": "text",
        "indexed": false,
        "description": "The extracted fact or summary text itself. Not indexed as it's the source of the vector."
      }
   }
}
```
