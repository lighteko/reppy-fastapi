"""
Local runner for development and testing.

Allows running the worker pipeline locally with JSON file or stdin input.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..contracts import WorkerRequest, ResultEvent
from ..pipelines import PipelineOrchestrator
from ..utils import setup_logging

logger = logging.getLogger(__name__)


async def run_pipeline(payload: Dict[str, Any]) -> ResultEvent:
    """
    Run the pipeline with a payload.
    
    Args:
        payload: Request payload dict.
        
    Returns:
        Result event.
    """
    async with PipelineOrchestrator() as orchestrator:
        request = WorkerRequest.model_validate(payload)
        result = await orchestrator.process(request)
        return result


def run_local(
    input_file: Optional[str] = None,
    input_json: Optional[str] = None,
    output_file: Optional[str] = None,
    pretty: bool = True,
) -> Dict[str, Any]:
    """
    Run the worker locally.
    
    Args:
        input_file: Path to JSON file with request payload.
        input_json: JSON string with request payload.
        output_file: Optional path to write result.
        pretty: Pretty print JSON output.
        
    Returns:
        Result dict.
    """
    setup_logging(level="DEBUG")
    
    # Load payload
    if input_file:
        logger.info(f"Loading payload from file: {input_file}")
        with open(input_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    elif input_json:
        logger.info("Loading payload from JSON string")
        payload = json.loads(input_json)
    else:
        logger.info("Reading payload from stdin")
        payload = json.load(sys.stdin)
    
    logger.info(f"Request ID: {payload.get('requestId', 'unknown')}")
    
    # Run pipeline
    result = asyncio.run(run_pipeline(payload))
    
    # Format output
    result_dict = result.model_dump(mode="json")
    
    if output_file:
        logger.info(f"Writing result to file: {output_file}")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2 if pretty else None)
    else:
        if pretty:
            print(json.dumps(result_dict, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result_dict, ensure_ascii=False))
    
    return result_dict


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run Reppy Worker locally for development and testing."
    )
    parser.add_argument(
        "-f", "--file",
        help="Path to JSON file with request payload",
    )
    parser.add_argument(
        "-j", "--json",
        help="JSON string with request payload",
    )
    parser.add_argument(
        "-o", "--output",
        help="Path to write result JSON",
    )
    parser.add_argument(
        "--no-pretty",
        action="store_true",
        help="Disable pretty printing",
    )
    parser.add_argument(
        "-e", "--example",
        action="store_true",
        help="Run with example payload",
    )
    
    args = parser.parse_args()
    
    if args.example:
        # Run with example payload
        example_payload = {
            "requestId": "test-123",
            "userId": "user-456",
            "conversation_history": [
                {"role": "user", "content": "오늘 운동 뭐 해야 돼?"}
            ],
            "stream": False,
            "metadata": {},
        }
        result = run_local(
            input_json=json.dumps(example_payload),
            output_file=args.output,
            pretty=not args.no_pretty,
        )
    elif args.file or args.json:
        result = run_local(
            input_file=args.file,
            input_json=args.json,
            output_file=args.output,
            pretty=not args.no_pretty,
        )
    else:
        # Read from stdin
        result = run_local(
            output_file=args.output,
            pretty=not args.no_pretty,
        )
    
    # Exit with appropriate code
    if result.get("status") == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()

