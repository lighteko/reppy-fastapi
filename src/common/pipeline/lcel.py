"""LCEL pipeline assembly: preprocess → agent → parse → validate → post."""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnablePassthrough,
    RunnableBranch,
)
from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger

from src.common.utils.validation import validate_response


def preprocess_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Preprocess inputs before agent execution.
    
    Args:
        inputs: Raw inputs from API.
        
    Returns:
        Processed inputs ready for agent.
    """
    logger.info("Preprocessing inputs")
    
    # Extract key fields
    user_input = inputs.get("input", "")
    context = inputs.get("context", {})
    prompt_data = inputs.get("prompt_data", {})
    
    # Format variables from prompt YAML into the input
    variables = prompt_data.get("variables", [])
    formatted_context = {}
    
    for var_spec in variables:
        var_name = var_spec.get("name")
        if var_name in context:
            # Convert to JSON string for template insertion
            formatted_context[f"{var_name}_json"] = json.dumps(context[var_name], indent=2)
    
    # Build the complete input for the agent
    # Flatten formatted_context to top level so prompt templates can access variables directly
    processed = {
        "input": user_input,
        **formatted_context,  # Flatten to top level for prompt template
        "context": context,  # Keep original context for other uses
        "prompt_data": prompt_data,
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": inputs.get("user_id"),
        },
    }
    
    logger.debug(f"Preprocessed input with {len(formatted_context)} context variables")
    return processed


def parse_llm_output(output: Any) -> Dict[str, Any]:
    """Parse LLM output (extract JSON from response).
    
    Args:
        output: Raw output from agent/LLM.
        
    Returns:
        Dict with parsed_output and raw_output.
    """
    logger.info("Parsing LLM output")
    
    # Handle different output types
    if isinstance(output, dict):
        if "output" in output:
            raw_text = output["output"]
        else:
            raw_text = json.dumps(output)
    elif isinstance(output, AIMessage):
        raw_text = output.content
    elif isinstance(output, str):
        raw_text = output
    else:
        raw_text = str(output)
    
    # Try to extract JSON from markdown blocks
    parsed_output = None
    
    # Remove markdown code blocks if present
    if "```json" in raw_text:
        start = raw_text.find("```json") + 7
        end = raw_text.find("```", start)
        if end > start:
            raw_text = raw_text[start:end].strip()
    elif "```" in raw_text:
        start = raw_text.find("```") + 3
        end = raw_text.find("```", start)
        if end > start:
            raw_text = raw_text[start:end].strip()
    
    # Try to parse as JSON
    try:
        parsed_output = json.loads(raw_text)
        logger.info("Successfully parsed JSON output")
    except json.JSONDecodeError:
        logger.warning("Failed to parse output as JSON, trying to find JSON object")
        
        # Try to find JSON object in text
        brace_start = raw_text.find("{")
        brace_end = raw_text.rfind("}")
        
        if brace_start >= 0 and brace_end > brace_start:
            try:
                parsed_output = json.loads(raw_text[brace_start:brace_end + 1])
                logger.info("Extracted JSON from text")
            except json.JSONDecodeError:
                logger.error("Could not extract valid JSON from output")
    
    return {
        "parsed_output": parsed_output,
        "raw_output": raw_text,
    }


def validate_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parsed output against schema.
    
    Args:
        data: Dict with parsed_output, prompt_data, etc.
        
    Returns:
        Dict with validation results.
    """
    logger.info("Validating output")
    
    parsed_output = data.get("parsed_output")
    prompt_data = data.get("prompt_data", {})
    context = data.get("context", {})
    
    if parsed_output is None:
        logger.error("No parsed output to validate")
        return {
            **data,
            "validation": {
                "valid": False,
                "errors": ["Failed to parse output as JSON"],
                "warnings": [],
            },
        }
    
    # Get prompt type
    prompt_type = prompt_data.get("prompt_type", "unknown")
    
    # Extract available_context if present
    available_context = None
    if "available_context" in context:
        # The context might have been JSON-stringified
        ac = context["available_context"]
        if isinstance(ac, str):
            try:
                available_context = json.loads(ac)
            except json.JSONDecodeError:
                available_context = None
        else:
            available_context = ac
    
    # Validate
    validation_result = validate_response(
        response_data=parsed_output,
        prompt_type=prompt_type,
        available_context=available_context,
    )
    
    logger.info(f"Validation result: valid={validation_result['valid']}, errors={len(validation_result['errors'])}")
    
    return {
        **data,
        "validation": validation_result,
    }


def repair_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """Attempt to repair invalid output (simplified - mark for regeneration).
    
    Args:
        data: Dict with validation results.
        
    Returns:
        Dict with repair status.
    """
    validation = data.get("validation", {})
    
    if validation.get("valid"):
        logger.info("Output is valid, no repair needed")
        return {
            **data,
            "repaired": False,
            "needs_regeneration": False,
        }
    
    errors = validation.get("errors", [])
    logger.warning(f"Output invalid with {len(errors)} errors, marking for regeneration")
    
    # For now, we'll mark for regeneration rather than attempting auto-repair
    # A more sophisticated implementation could try to fix common issues
    
    return {
        **data,
        "repaired": False,
        "needs_regeneration": True,
    }


def postprocess_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """Postprocess and attach metadata & citations.
    
    Args:
        data: Dict with final output.
        
    Returns:
        Final formatted response.
    """
    logger.info("Postprocessing output")
    
    validation = data.get("validation", {})
    validated_data = validation.get("validated_data")
    metadata = data.get("metadata", {})
    
    # Build final response
    response = {
        "success": validation.get("valid", False),
        "data": validated_data,
        "metadata": {
            **metadata,
            "processed_at": datetime.utcnow().isoformat(),
        },
        "validation": {
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
        },
    }
    
    # Add citations if tool calls were made
    # (This would be populated by the callback handler)
    tool_calls = data.get("tool_calls", [])
    if tool_calls:
        response["citations"] = {
            "tool_calls_count": len(tool_calls),
            "tools_used": list(set(tc.get("tool_name") for tc in tool_calls if tc.get("tool_name"))),
        }
    
    logger.info("Postprocessing complete")
    return response


def build_lcel_pipeline(agent: Runnable) -> Runnable:
    """Build the complete LCEL pipeline.
    
    Args:
        agent: The agent runnable (from agent_builder).
        
    Returns:
        Complete LCEL pipeline.
    """
    logger.info("Building LCEL pipeline")
    
    # Build the pipeline
    pipeline = (
        RunnableLambda(preprocess_input)
        | RunnablePassthrough.assign(
            agent_output=agent
        )
        | RunnableLambda(lambda x: {**x, **parse_llm_output(x.get("agent_output"))})
        | RunnableLambda(validate_output)
        | RunnableBranch(
            # If needs regeneration, we could loop back, but for now just mark it
            (lambda x: x.get("needs_regeneration", False), RunnableLambda(repair_output)),
            # Otherwise, continue
            RunnableLambda(lambda x: x),
        )
        | RunnableLambda(postprocess_output)
    )
    
    logger.info("LCEL pipeline built successfully")
    return pipeline


def build_streaming_pipeline(agent: Runnable) -> Runnable:
    """Build a streaming version of the pipeline.
    
    Args:
        agent: The agent runnable.
        
    Returns:
        Streaming LCEL pipeline.
    """
    logger.info("Building streaming LCEL pipeline")
    
    # For streaming, we simplify - just preprocess and run agent
    # Postprocessing happens client-side
    pipeline = (
        RunnableLambda(preprocess_input)
        | agent
    )
    
    logger.info("Streaming pipeline built successfully")
    return pipeline

