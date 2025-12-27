"""Local runner for testing and development."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from src.config import Settings
from src.context.adapters.aggregator import DefaultContextAggregator
from src.context.adapters.vm_client import VMApiClient
from src.contracts.messages import RequestPayload
from src.emit.oci_streaming import LocalTokenStreamer
from src.emit.result_queue import LocalResultPublisher
from src.pipelines.orchestrator import PipelineOrchestrator
from src.utils.logging import configure_logging

logger = logging.getLogger(__name__)


def create_mock_settings() -> Settings:
    """
    Create settings with mock values for local testing.
    
    In local mode, some values can be mocked or use env defaults.
    """
    import os
    
    # Set defaults for optional local testing
    os.environ.setdefault("GOOGLE_API_KEY", "your-api-key-here")
    os.environ.setdefault("VM_INTERNAL_BASE_URL", "http://localhost:8080/internal")
    os.environ.setdefault("VM_INTERNAL_TOKEN", "local-dev-token")
    os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
    os.environ.setdefault("OCI_STREAM_ID", "local-stream")
    os.environ.setdefault("OCI_RESULT_QUEUE_ID", "local-queue")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    
    return Settings()  # type: ignore[call-arg]


class MockVMClient(VMApiClient):
    """Mock VM client for local testing."""

    async def claim_idempotency(self, request_id: str) -> bool:
        """Always claim successfully in local mode."""
        logger.debug(f"[Mock] Claiming {request_id}")
        return True

    async def get_user_profile(self, user_id: str) -> dict:
        """Return mock user profile."""
        return {
            "userId": user_id,
            "username": "TestUser",
            "experience_level": "INTERMEDIATE",
            "goal": "HYPERTROPHY",
            "unit_system": "CM_KG",
            "locale": "ko-KR",
        }

    async def get_active_routines(self, user_id: str) -> dict:
        """Return mock routines."""
        return {
            "routines": [
                {
                    "routine_name": "Push Day",
                    "routine_order": 1,
                    "plans": [
                        {
                            "exercise_code": "BARBELL_BENCH_PRESS",
                            "plan_order": 1,
                            "sets": [
                                {"set_type_code": "NORMAL", "set_order": 1, "reps": 8, "weight": 60, "rest_time": 90}
                            ]
                        }
                    ]
                }
            ]
        }

    async def search_exercises(self, query: str) -> dict:
        """Return mock exercise search results."""
        return {
            "items": [
                {"exercise_code": "DUMBBELL_BENCH_PRESS", "name": "덤벨 벤치프레스", "main_muscle_code": "CHEST"},
                {"exercise_code": "INCLINE_BENCH_PRESS", "name": "인클라인 벤치프레스", "main_muscle_code": "CHEST"},
            ]
        }


async def run_local(payload_path: str | None, payload_json: str | None) -> None:
    """
    Run the worker locally with a payload.
    
    Args:
        payload_path: Path to JSON file with payload.
        payload_json: JSON string payload.
    """
    settings = create_mock_settings()
    configure_logging(settings)

    logger.info("Starting local runner")

    # Load payload
    if payload_path:
        with open(payload_path) as f:
            payload_data = json.load(f)
    elif payload_json:
        payload_data = json.loads(payload_json)
    else:
        # Read from stdin
        logger.info("Reading payload from stdin (enter JSON, then Ctrl+D):")
        payload_data = json.load(sys.stdin)

    # Parse payload
    payload = RequestPayload.model_validate(payload_data)
    logger.info(f"Loaded payload for request {payload.request_id}")

    # Create mock/local components
    vm_client = MockVMClient(settings)
    context_aggregator = DefaultContextAggregator(settings, vm_client)
    token_streamer = LocalTokenStreamer()
    result_publisher = LocalResultPublisher()

    orchestrator = PipelineOrchestrator(
        settings=settings,
        vm_client=vm_client,
        context_aggregator=context_aggregator,
        token_streamer=token_streamer,
        result_publisher=result_publisher,
    )

    try:
        # Process
        await orchestrator.process(payload)
        
        # Show results
        results = result_publisher.get_results()
        if results:
            logger.info(f"Processing complete. {len(results)} result(s) published.")
        else:
            logger.warning("No results published")

    finally:
        await vm_client.close()
        await context_aggregator.close()


def main() -> None:
    """Main entry point for local runner."""
    parser = argparse.ArgumentParser(
        description="Reppy Worker Local Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with JSON file
  python -m src.entrypoints.local_runner -f payload.json

  # Run with inline JSON
  python -m src.entrypoints.local_runner -j '{"requestId": "...", ...}'

  # Run with stdin
  cat payload.json | python -m src.entrypoints.local_runner
        """,
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Path to JSON file with request payload",
    )
    parser.add_argument(
        "-j", "--json",
        type=str,
        help="JSON string with request payload",
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_local(args.file, args.json))
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

