"""Usage examples for Reppy RAG pipeline."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from src.config import get_config
from src.common.prompts import load_prompt, list_prompts
from src.common.action_router import route_input
from src.common.tools import ReppyTools
from src.common.agent_builder import build_tool_calling_agent
from src.common.executor import make_agent_executor
from src.common.lcel_pipeline import build_lcel_pipeline
from src.common.rag_retriever import QdrantRetriever
from src.infra.express_client import ExpressAPIClient
from src.infra.qdrant_client import QdrantVectorDB


async def example_mode_a():
    """Example of Mode A: Route and execute."""
    print("\n=== Mode A: Route and Execute ===\n")
    
    # User input
    user_input = "I want to generate a new workout program for hypertrophy"
    user_id = "test-user-123"
    
    # Route to appropriate prompt
    prompt_key, scores = route_input(user_input)
    print(f"Routed to: {prompt_key}")
    print(f"Scores: {scores}\n")
    
    # Load prompt
    prompt_data = load_prompt(prompt_key)
    print(f"Loaded prompt type: {prompt_data.get('prompt_type')}")
    
    # Initialize clients
    express_client = ExpressAPIClient()
    qdrant_client = QdrantVectorDB()
    retriever = QdrantRetriever(qdrant_client=qdrant_client)
    
    # Create tools
    tools_factory = ReppyTools(
        express_client=express_client,
        retriever=retriever,
        user_id=user_id,
    )
    tools = tools_factory.get_tools_for_prompt(prompt_data)
    print(f"Created {len(tools)} tools\n")
    
    # Build agent
    agent = build_tool_calling_agent(
        prompt_yaml=prompt_data,
        tools=tools,
    )
    
    # Build executor
    executor = make_agent_executor(
        agent=agent,
        tools=tools,
        user_id=user_id,
    )
    
    # Build pipeline
    pipeline = build_lcel_pipeline(executor)
    
    # Execute
    context = {
        "user_profile": {
            "goal": "HYPERTROPHY",
            "experience_level": "INTERMEDIATE",
            "unit_system": "CM_KG",
        },
        "job_context": {
            "program_name": "Summer Gains",
            "start_date": "2025-11-01",
            "goal_date": "2025-12-31",
        },
        "available_context": {
            "exercises": [
                {"exercise_code": "BARBELL_BENCH_PRESS", "main_muscle_code": "CHEST"},
                {"exercise_code": "BARBELL_SQUAT", "main_muscle_code": "LEGS"},
            ],
            "set_types": [
                {"set_type_code": "NORMAL"},
                {"set_type_code": "WARMUP"},
            ],
        },
    }
    
    pipeline_input = {
        "input": user_input,
        "context": context,
        "prompt_data": prompt_data,
        "user_id": user_id,
    }
    
    print("Executing pipeline...")
    # Note: This would actually call the LLM and tools
    # result = await pipeline.ainvoke(pipeline_input)
    # print(f"\nResult: {result}")
    
    await express_client.close()
    print("\nMode A complete!")


async def example_mode_b():
    """Example of Mode B: Direct execution."""
    print("\n=== Mode B: Direct Execute ===\n")
    
    # Specify prompt directly
    prompt_key = "chat_response"
    user_input = "What's a good alternative to bench press?"
    user_id = "test-user-123"
    
    print(f"Using prompt: {prompt_key}\n")
    
    # Load prompt
    prompt_data = load_prompt(prompt_key)
    
    # Initialize clients
    express_client = ExpressAPIClient()
    qdrant_client = QdrantVectorDB()
    retriever = QdrantRetriever(qdrant_client=qdrant_client)
    
    # Create tools
    tools_factory = ReppyTools(
        express_client=express_client,
        retriever=retriever,
        user_id=user_id,
    )
    tools = tools_factory.get_tools_for_prompt(prompt_data)
    
    # Build and execute agent
    agent = build_tool_calling_agent(prompt_yaml=prompt_data, tools=tools)
    executor = make_agent_executor(agent=agent, tools=tools, user_id=user_id)
    pipeline = build_lcel_pipeline(executor)
    
    context = {
        "user_profile": {
            "username": "Alex",
            "experience_level": "INTERMEDIATE",
            "goal": "HYPERTROPHY",
        },
        "conversation_history": [
            {"role": "user", "content": user_input},
        ],
    }
    
    pipeline_input = {
        "input": user_input,
        "context": context,
        "prompt_data": prompt_data,
        "user_id": user_id,
    }
    
    print("Executing pipeline...")
    result = await pipeline.ainvoke(pipeline_input)
    print(f"\nResult: {result}")
    
    await express_client.close()
    print("\nMode B complete!")


async def example_list_prompts():
    """Example of listing available prompts."""
    print("\n=== List Available Prompts ===\n")
    
    prompts = list_prompts()
    print(f"Available prompts ({len(prompts)}):")
    for prompt in prompts:
        print(f"  - {prompt}")
    
    print("\nDetails for each prompt:")
    for prompt_key in prompts:
        prompt_data = load_prompt(prompt_key)
        prompt_type = prompt_data.get("prompt_type")
        tools = prompt_data.get("tools", [])
        print(f"\n  {prompt_key}:")
        print(f"    Type: {prompt_type}")
        print(f"    Tools: {len(tools)}")
        print(f"    Tool names: {[t.get('name') for t in tools]}")


async def example_router_analysis():
    """Example of router decision analysis."""
    print("\n=== Router Analysis ===\n")
    
    test_inputs = [
        "Generate a new program for me",
        "Update my bench press to be harder",
        "What's the best exercise for chest?",
        "Based on my 1RM, create a strength program",
    ]
    
    for user_input in test_inputs:
        prompt_key, scores = route_input(user_input)
        print(f"Input: '{user_input}'")
        print(f"  → Routed to: {prompt_key}")
        print(f"  → Scores: {scores}\n")


async def example_health_check():
    """Example of health checks."""
    print("\n=== Health Check ===\n")
    
    # Qdrant health
    qdrant = QdrantVectorDB()
    health = qdrant.health()
    print(f"Qdrant: {health['status']}")
    if health['status'] == 'healthy':
        print(f"  Collections: {health.get('collections', [])}")
    
    # Express health (would require server to be running)
    # express = ExpressAPIClient()
    # try:
    #     await express.get("/health")
    #     print("Express: healthy")
    # except Exception as e:
    #     print(f"Express: unhealthy - {e}")
    # finally:
    #     await express.close()


async def main():
    """Run all examples."""
    print("\n" + "="*50)
    print("  Reppy RAG Pipeline - Usage Examples")
    print("="*50)
    
    # Run examples
    await example_list_prompts()
    await example_router_analysis()
    # await example_health_check()
    
    # These require actual LLM/API access
    # await example_mode_a()
    await example_mode_b()
    
    print("\n" + "="*50)
    print("  Examples complete!")
    print("="*50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

