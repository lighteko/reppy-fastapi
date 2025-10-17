"""AWS Lambda handler for processing SQS messages."""

import json
import asyncio
from typing import Any, Dict
from datetime import datetime

from loguru import logger

from src.common.prompts import load_prompt
from src.common.tools import ReppyTools
from src.common.agent_builder import build_tool_calling_agent
from src.common.executor import make_agent_executor
from src.common.lcel_pipeline import build_lcel_pipeline
from src.common.rag_retriever import QdrantRetriever
from src.infra.express_client import ExpressAPIClient
from src.infra.qdrant_client import QdrantVectorDB
from src.config import get_config


async def process_generate_program_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process a generate_program job.
    
    Args:
        payload: Job payload with user_id, program_id, context, etc.
        
    Returns:
        Processing result.
    """
    user_id = payload.get("user_id")
    program_id = payload.get("program_id")
    context = payload.get("context", {})
    input_text = payload.get("input", "Generate a new workout program")
    
    logger.info(f"Processing generate_program job for user {user_id}, program {program_id}")
    
    try:
        # Load prompt
        prompt_data = load_prompt("generate_program")
        
        # Initialize clients
        express_client = ExpressAPIClient()
        qdrant_client = QdrantVectorDB()
        retriever = QdrantRetriever(qdrant_client=qdrant_client)
        
        # Fetch additional context from Express API
        user_profile = await express_client.get_user_profile(user_id)
        context["user_profile"] = user_profile
        
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
        
        # Build pipeline
        pipeline = build_lcel_pipeline(executor)
        
        # Execute
        pipeline_input = {
            "input": input_text,
            "context": context,
            "prompt_data": prompt_data,
            "user_id": user_id,
        }
        
        result = await pipeline.ainvoke(pipeline_input)
        
        # If successful, save routines via Express API
        if result.get("success") and result.get("data"):
            routines_data = result["data"].get("routines", [])
            
            if routines_data:
                save_result = await express_client.save_batch_routines(
                    user_id=user_id,
                    program_id=program_id,
                    routines=routines_data,
                )
                logger.info(f"Saved {len(routines_data)} routines to Express API")
                result["save_result"] = save_result
        
        # Close clients
        await express_client.close()
        
        return {
            "success": True,
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"Job processing failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def process_update_routine_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process an update_routine job.
    
    Args:
        payload: Job payload.
        
    Returns:
        Processing result.
    """
    user_id = payload.get("user_id")
    routine_id = payload.get("routine_id")
    context = payload.get("context", {})
    input_text = payload.get("input", "")
    
    logger.info(f"Processing update_routine job for user {user_id}, routine {routine_id}")
    
    try:
        # Similar to generate_program but for updates
        prompt_data = load_prompt("update_routine")
        
        express_client = ExpressAPIClient()
        qdrant_client = QdrantVectorDB()
        retriever = QdrantRetriever(qdrant_client=qdrant_client)
        
        # Fetch user profile
        user_profile = await express_client.get_user_profile(user_id)
        context["user_profile"] = user_profile
        
        # Create tools
        tools_factory = ReppyTools(
            express_client=express_client,
            retriever=retriever,
            user_id=user_id,
        )
        tools = tools_factory.get_tools_for_prompt(prompt_data)
        
        # Build and execute
        agent = build_tool_calling_agent(prompt_yaml=prompt_data, tools=tools)
        executor = make_agent_executor(agent=agent, tools=tools, user_id=user_id)
        pipeline = build_lcel_pipeline(executor)
        
        pipeline_input = {
            "input": input_text,
            "context": context,
            "prompt_data": prompt_data,
            "user_id": user_id,
        }
        
        result = await pipeline.ainvoke(pipeline_input)
        
        # Save updated routine if successful
        if result.get("success") and result.get("data"):
            # Call Express API to update the routine
            # This would be a PUT/PATCH endpoint
            logger.info("Updated routine ready to save")
            # TODO: Implement save_updated_routine on express_client
        
        await express_client.close()
        
        return {
            "success": True,
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"Job processing failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def process_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single SQS message.
    
    Args:
        message: SQS message dict.
        
    Returns:
        Processing result.
    """
    try:
        # Parse message body
        body = json.loads(message["body"])
        job_type = body.get("job_type")
        payload = body.get("payload", {})
        
        logger.info(f"Processing message: job_type={job_type}")
        
        # Route to appropriate handler
        if job_type == "generate_program":
            result = await process_generate_program_job(payload)
        elif job_type == "update_routine":
            result = await process_update_routine_job(payload)
        else:
            logger.warning(f"Unknown job type: {job_type}")
            result = {
                "success": False,
                "error": f"Unknown job type: {job_type}",
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Message processing error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SQS events.
    
    Args:
        event: Lambda event dict with SQS records.
        context: Lambda context.
        
    Returns:
        Response dict with processing results.
    """
    logger.info(f"Lambda invoked with {len(event.get('Records', []))} records")
    
    # Process records
    results = []
    failed_message_ids = []
    
    for record in event.get("Records", []):
        message_id = record.get("messageId")
        
        try:
            # Run async processing
            result = asyncio.run(process_message(record))
            
            if result.get("success"):
                logger.info(f"Successfully processed message {message_id}")
                results.append({
                    "messageId": message_id,
                    "status": "success",
                })
            else:
                logger.error(f"Failed to process message {message_id}: {result.get('error')}")
                failed_message_ids.append(message_id)
                results.append({
                    "messageId": message_id,
                    "status": "failed",
                    "error": result.get("error"),
                })
                
        except Exception as e:
            logger.error(f"Exception processing message {message_id}: {e}")
            failed_message_ids.append(message_id)
            results.append({
                "messageId": message_id,
                "status": "error",
                "error": str(e),
            })
    
    # Return batch item failures for SQS to retry
    response = {
        "batchItemFailures": [
            {"itemIdentifier": msg_id}
            for msg_id in failed_message_ids
        ]
    }
    
    logger.info(f"Processed {len(results)} messages, {len(failed_message_ids)} failed")
    return response

