"""Common modules for Reppy RAG pipeline.

Modularized structure:
- agents/: Agent building and execution
- pipeline/: Pipeline orchestration and routing
- tools/: Tool implementations and RAG retrieval
- utils/: Utilities (prompts, validation, observability)
"""

# Import from submodules for backward compatibility
from .agents import (
    build_tool_calling_agent,
    build_simple_llm_chain,
    make_agent_executor,
    run_agent_with_retry,
)
from .pipeline import (
    build_lcel_pipeline,
    build_streaming_pipeline,
    LLMActionRouter,
    route_input_llm,
    route_input_llm_sync,
    get_llm_router,
)
from .tools import (
    ReppyTools,
    QdrantRetriever,
)
from .utils import (
    load_prompt,
    list_prompts,
    get_prompt_loader,
    validate_response,
    DomainValidator,
    ChatResponse,
    GenerateProgramResponse,
    UpdateRoutineResponse,
    setup_logging,
    setup_langsmith,
    ReppyCallbackHandler,
)

__all__ = [
    # Agents
    "build_tool_calling_agent",
    "build_simple_llm_chain",
    "make_agent_executor",
    "run_agent_with_retry",
    # Pipeline
    "build_lcel_pipeline",
    "build_streaming_pipeline",
    "LLMActionRouter",
    "route_input_llm",
    "route_input_llm_sync",
    "get_llm_router",
    # Tools
    "ReppyTools",
    "QdrantRetriever",
    # Utils
    "load_prompt",
    "list_prompts",
    "get_prompt_loader",
    "validate_response",
    "DomainValidator",
    "ChatResponse",
    "GenerateProgramResponse",
    "UpdateRoutineResponse",
    "setup_logging",
    "setup_langsmith",
    "ReppyCallbackHandler",
]

