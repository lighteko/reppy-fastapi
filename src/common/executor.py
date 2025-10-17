"""Agent executor: make_agent_executor(agent, tools, **opts) -> AgentExecutor."""

from typing import Any, Dict, List, Optional

from langchain.agents import AgentExecutor
from langchain_core.runnables import Runnable
from langchain_core.tools import StructuredTool
from langchain_core.callbacks import BaseCallbackHandler
from loguru import logger

from src.config import get_config
from src.common.observability import ReppyCallbackHandler


def make_agent_executor(
    agent: Runnable,
    tools: List[StructuredTool],
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    config: Optional[Any] = None,
    **kwargs,
) -> AgentExecutor:
    """Create an AgentExecutor with proper configuration.
    
    Args:
        agent: The agent runnable.
        tools: List of tools available to the agent.
        callbacks: Optional list of callback handlers.
        user_id: Optional user ID for tracking.
        session_id: Optional session ID for tracking.
        config: Optional configuration object.
        **kwargs: Additional AgentExecutor options.
        
    Returns:
        Configured AgentExecutor.
    """
    cfg = config or get_config()
    
    # Setup callbacks
    if callbacks is None:
        callbacks = []
    
    # Add default callback handler
    reppy_callback = ReppyCallbackHandler(user_id=user_id, session_id=session_id)
    callbacks.append(reppy_callback)
    
    # Build executor config
    executor_config = {
        "agent": agent,
        "tools": tools,
        "callbacks": callbacks,
        "verbose": True,
        "max_iterations": kwargs.get("max_iterations", cfg.agent_max_iterations),
        "max_execution_time": kwargs.get("max_execution_time", cfg.tool_timeout),
        "handle_parsing_errors": True,
        "return_intermediate_steps": True,
    }
    
    # Create executor
    executor = AgentExecutor(**executor_config)
    
    logger.info(
        f"Created AgentExecutor with {len(tools)} tools, "
        f"max_iterations={executor_config['max_iterations']}"
    )
    
    return executor


async def run_agent_with_retry(
    executor: AgentExecutor,
    input_data: Dict[str, Any],
    max_retries: Optional[int] = None,
    config: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run agent executor with retry logic on parsing errors.
    
    Args:
        executor: The AgentExecutor instance.
        input_data: Input data for the agent.
        max_retries: Maximum number of retries on parsing errors.
        config: Optional configuration object.
        
    Returns:
        Agent execution result.
    """
    cfg = config or get_config()
    max_retries = max_retries or cfg.agent_parsing_retries
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Running agent (attempt {attempt + 1}/{max_retries + 1})")
            result = await executor.ainvoke(input_data)
            logger.info("Agent execution successful")
            return result
            
        except Exception as e:
            last_error = e
            logger.warning(f"Agent execution failed (attempt {attempt + 1}): {e}")
            
            # Check if it's a parsing error or other recoverable error
            error_str = str(e).lower()
            is_parsing_error = any(
                keyword in error_str
                for keyword in ["parse", "json", "format", "invalid"]
            )
            
            if not is_parsing_error or attempt >= max_retries:
                # Non-parsing error or out of retries
                break
            
            logger.info(f"Retrying due to parsing error...")
    
    # All retries exhausted
    logger.error(f"Agent execution failed after {max_retries + 1} attempts")
    raise last_error


def make_simple_executor(
    chain: Runnable,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Runnable:
    """Create a simple executor for chains without tools.
    
    Args:
        chain: The LLM chain runnable.
        callbacks: Optional list of callback handlers.
        user_id: Optional user ID.
        session_id: Optional session ID.
        
    Returns:
        The chain with callbacks configured.
    """
    # Setup callbacks
    if callbacks is None:
        callbacks = []
    
    # Add default callback handler
    reppy_callback = ReppyCallbackHandler(user_id=user_id, session_id=session_id)
    callbacks.append(reppy_callback)
    
    # Return chain with callbacks
    chain_with_callbacks = chain.with_config({"callbacks": callbacks})
    
    logger.info("Created simple executor for chain")
    return chain_with_callbacks

