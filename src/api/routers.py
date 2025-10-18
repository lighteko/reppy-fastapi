"""FastAPI routers for Mode A (routing) and Mode B (direct execution)."""

from typing import Any, Dict, List, Optional
from uuid import UUID
import asyncio

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger

from src.common import (
    load_prompt,
    list_prompts,
    route_input_llm,
    ReppyTools,
    build_tool_calling_agent,
    make_agent_executor,
    run_agent_with_retry,
    build_lcel_pipeline,
    QdrantRetriever,
)
from src.infra.express_client import ExpressAPIClient
from src.infra.qdrant_client import QdrantVectorDB


# Request/Response Models

class ModeARequest(BaseModel):
    """Request for Mode A (with routing)."""
    input: str = Field(description="User input text")
    user_id: str = Field(description="User ID for context")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context variables")
    stream: bool = Field(default=False, description="Whether to stream the response")


class ModeBRequest(BaseModel):
    """Request for Mode B (direct execution)."""
    prompt_key: str = Field(description="Prompt key to use directly")
    input: str = Field(description="User input text")
    user_id: str = Field(description="User ID for context")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context variables")
    stream: bool = Field(default=False, description="Whether to stream the response")


class PromptListResponse(BaseModel):
    """Response listing available prompts."""
    prompts: List[str] = Field(description="List of available prompt keys")


class ExecutionResponse(BaseModel):
    """Response from pipeline execution."""
    success: bool = Field(description="Whether execution succeeded")
    prompt_key: str = Field(description="Prompt key that was used")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Validated output data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
    validation: Dict[str, Any] = Field(default_factory=dict, description="Validation results")
    citations: Optional[Dict[str, Any]] = Field(default=None, description="Tool citations")


# Router

router = APIRouter(prefix="/api/v1", tags=["rag"])


# Helper Functions

async def execute_pipeline(
    prompt_key: str,
    user_input: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute the complete RAG pipeline for a given prompt.
    
    Args:
        prompt_key: The prompt key to use.
        user_input: User's input text.
        user_id: User ID.
        context: Optional context variables.
        
    Returns:
        Execution result dict.
    """
    context = context or {}
    
    try:
        # Load prompt
        prompt_data = load_prompt(prompt_key)
        logger.info(f"Loaded prompt: {prompt_key}")
        
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
        
        # Build LCEL pipeline
        pipeline = build_lcel_pipeline(executor)
        
        # Prepare input
        pipeline_input = {
            "input": user_input,
            "context": context,
            "prompt_data": prompt_data,
            "user_id": user_id,
        }
        
        # Execute pipeline
        result = await pipeline.ainvoke(pipeline_input)
        
        # Close clients
        await express_client.close()
        
        # Add prompt_key to result
        result["prompt_key"] = prompt_key
        
        return result
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)}",
        )


# Endpoints

@router.get("/prompts", response_model=PromptListResponse)
async def get_available_prompts():
    """List all available prompts.
    
    Returns:
        List of prompt keys.
    """
    prompts = list_prompts()
    return PromptListResponse(prompts=prompts)


@router.post("/route", response_model=ExecutionResponse)
async def mode_a_route_and_execute(request: ModeARequest):
    """Mode A: Route input to appropriate prompt and execute.
    
    Args:
        request: Mode A request with input and context.
        
    Returns:
        Execution result.
    """
    logger.info(f"Mode A request from user {request.user_id}")
    
    # Route using LLM
    prompt_key, metadata = await route_input_llm(request.input, request.context)
    logger.info(f"LLM routed to prompt: {prompt_key} (metadata: {metadata})")
    
    # Execute pipeline
    result = await execute_pipeline(
        prompt_key=prompt_key,
        user_input=request.input,
        user_id=request.user_id,
        context=request.context,
    )
    
    # Add routing metadata to result
    if "metadata" not in result:
        result["metadata"] = {}
    result["metadata"]["routing_method"] = "llm"
    result["metadata"]["routing_info"] = metadata
    
    return ExecutionResponse(**result)


@router.post("/run", response_model=ExecutionResponse)
async def mode_b_direct_execute(request: ModeBRequest):
    """Mode B: Execute with specified prompt directly.
    
    Args:
        request: Mode B request with prompt key and input.
        
    Returns:
        Execution result.
    """
    logger.info(f"Mode B request from user {request.user_id} with prompt {request.prompt_key}")
    
    # Validate prompt exists
    available_prompts = list_prompts()
    if request.prompt_key not in available_prompts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{request.prompt_key}' not found. Available: {available_prompts}",
        )
    
    # Execute pipeline
    result = await execute_pipeline(
        prompt_key=request.prompt_key,
        user_input=request.input,
        user_id=request.user_id,
        context=request.context,
    )
    
    return ExecutionResponse(**result)


@router.post("/route/stream")
async def mode_a_route_and_stream(request: ModeARequest):
    """Mode A with streaming: Route and execute with streaming response.
    
    Args:
        request: Mode A request.
        
    Returns:
        Streaming response.
    """
    logger.info(f"Mode A streaming request from user {request.user_id}")
    
    # Route to appropriate prompt
    prompt_key, scores = route_input(request.input, request.context)
    logger.info(f"Routed to prompt: {prompt_key}")
    
    # TODO: Implement streaming version
    # For now, return error
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Streaming not yet implemented",
    )


@router.post("/run/stream")
async def mode_b_direct_stream(request: ModeBRequest):
    """Mode B with streaming: Execute with streaming response.
    
    Args:
        request: Mode B request.
        
    Returns:
        Streaming response.
    """
    logger.info(f"Mode B streaming request from user {request.user_id}")
    
    # TODO: Implement streaming version
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Streaming not yet implemented",
    )


@router.get("/health")
async def health_check():
    """Health check endpoint.
    
    Returns:
        Health status.
    """
    try:
        # Check Qdrant
        qdrant = QdrantVectorDB()
        qdrant_health = qdrant.health()
        
        # Check Express API
        express = ExpressAPIClient()
        try:
            # Simple health check - try to access base URL
            await express.get("/health")
            express_health = {"status": "healthy"}
        except Exception as e:
            express_health = {"status": "unhealthy", "error": str(e)}
        finally:
            await express.close()
        
        overall_status = (
            "healthy"
            if qdrant_health["status"] == "healthy" and express_health["status"] == "healthy"
            else "degraded"
        )
        
        return {
            "status": overall_status,
            "services": {
                "qdrant": qdrant_health,
                "express": express_health,
            },
            "prompts": list_prompts(),
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}",
        )

