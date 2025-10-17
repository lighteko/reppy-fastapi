"""Agent builder: build_tool_calling_agent(prompt_yaml, tools) -> Runnable."""

from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain.agents import create_tool_calling_agent
from langchain_core.tools import StructuredTool
from loguru import logger

from src.config import get_config


def format_prompt_from_yaml(prompt_data: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Format the prompt template using YAML data and context.
    
    Args:
        prompt_data: Parsed YAML prompt data.
        context: Context variables to inject.
        
    Returns:
        Formatted prompt string.
    """
    # Extract components from YAML
    role = prompt_data.get("role", "")
    instruction = prompt_data.get("instruction", "")
    
    # Format instruction with context variables
    formatted_instruction = instruction
    for key, value in context.items():
        placeholder = f"{{{key}}}"
        if placeholder in formatted_instruction:
            formatted_instruction = formatted_instruction.replace(placeholder, str(value))
    
    # Combine role and instruction
    full_prompt = f"{role}\n\n{formatted_instruction}"
    
    return full_prompt


def build_tool_calling_agent(
    prompt_yaml: Dict[str, Any],
    tools: List[StructuredTool],
    llm: Optional[Any] = None,
    config: Optional[Any] = None,
) -> Runnable:
    """Build a tool-calling agent from a prompt YAML and tools.
    
    Args:
        prompt_yaml: Parsed prompt YAML data.
        tools: List of LangChain StructuredTool instances.
        llm: Optional LLM instance. If None, creates ChatOpenAI.
        config: Optional configuration object.
        
    Returns:
        Runnable agent.
    """
    cfg = config or get_config()
    
    # Initialize LLM if not provided
    if llm is None:
        llm = ChatOpenAI(
            model=cfg.llm_model,
            temperature=cfg.llm_temperature,
            max_tokens=cfg.llm_max_tokens,
            openai_api_key=cfg.openai_api_key,
            timeout=cfg.llm_timeout,
        )
    
    # Build prompt template
    role = prompt_yaml.get("role", "")
    instruction = prompt_yaml.get("instruction", "")
    
    # Create chat prompt with placeholders for agent scaffolding
    system_message = f"{role}\n\n{instruction}"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    
    # Create the agent
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )
    
    logger.info(f"Built tool-calling agent with {len(tools)} tools")
    return agent


def build_simple_llm_chain(
    prompt_yaml: Dict[str, Any],
    llm: Optional[Any] = None,
    config: Optional[Any] = None,
) -> Runnable:
    """Build a simple LLM chain without tools (for chat-only scenarios).
    
    Args:
        prompt_yaml: Parsed prompt YAML data.
        llm: Optional LLM instance.
        config: Optional configuration object.
        
    Returns:
        Runnable LLM chain.
    """
    cfg = config or get_config()
    
    # Initialize LLM if not provided
    if llm is None:
        llm = ChatOpenAI(
            model=cfg.llm_model,
            temperature=cfg.llm_temperature,
            max_tokens=cfg.llm_max_tokens,
            openai_api_key=cfg.openai_api_key,
            timeout=cfg.llm_timeout,
        )
    
    # Build prompt template
    role = prompt_yaml.get("role", "")
    instruction = prompt_yaml.get("instruction", "")
    
    system_message = f"{role}\n\n{instruction}"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
    ])
    
    # Create simple chain
    chain = prompt | llm
    
    logger.info("Built simple LLM chain")
    return chain

