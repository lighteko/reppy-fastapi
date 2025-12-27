"""Pytest configuration and fixtures."""

import os
import pytest


@pytest.fixture(autouse=True)
def setup_test_env() -> None:
    """Set up test environment variables."""
    os.environ.setdefault("GOOGLE_API_KEY", "test-api-key")
    os.environ.setdefault("VM_INTERNAL_BASE_URL", "http://localhost:8080/internal")
    os.environ.setdefault("VM_INTERNAL_TOKEN", "test-token")
    os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
    os.environ.setdefault("OCI_STREAM_ID", "test-stream")
    os.environ.setdefault("OCI_RESULT_QUEUE_ID", "test-queue")

