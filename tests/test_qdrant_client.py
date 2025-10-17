"""Tests for Qdrant client."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.infra.qdrant_client import QdrantVectorDB
from src.config import get_config


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = Mock()
    config.qdrant_url = "http://localhost:6333"
    config.qdrant_api_key = None
    config.qdrant_grpc = False
    return config


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    with patch("src.infra.qdrant_client.QdrantClient") as mock:
        yield mock


def test_qdrant_initialization(mock_config, mock_qdrant_client):
    """Test Qdrant client initialization."""
    client = QdrantVectorDB(config=mock_config)
    
    assert client is not None
    assert client.config == mock_config
    mock_qdrant_client.assert_called_once()


def test_health_check_success(mock_config, mock_qdrant_client):
    """Test successful health check."""
    # Setup mock
    mock_instance = mock_qdrant_client.return_value
    mock_collections = Mock()
    mock_collections.collections = [
        Mock(name="exercises"),
        Mock(name="user_memory"),
    ]
    mock_instance.get_collections.return_value = mock_collections
    
    client = QdrantVectorDB(config=mock_config)
    health = client.health()
    
    assert health["status"] == "healthy"
    assert "exercises" in health["collections"]
    assert "user_memory" in health["collections"]


def test_health_check_failure(mock_config, mock_qdrant_client):
    """Test health check failure."""
    # Setup mock to raise exception
    mock_instance = mock_qdrant_client.return_value
    mock_instance.get_collections.side_effect = Exception("Connection failed")
    
    client = QdrantVectorDB(config=mock_config)
    health = client.health()
    
    assert health["status"] == "unhealthy"
    assert "error" in health


def test_search_with_filters(mock_config, mock_qdrant_client):
    """Test search with filter conditions."""
    # Setup mock
    mock_instance = mock_qdrant_client.return_value
    mock_result = Mock()
    mock_result.id = "test-id"
    mock_result.score = 0.95
    mock_result.payload = {"name": "Test Exercise", "exercise_code": "TEST"}
    mock_instance.search.return_value = [mock_result]
    
    client = QdrantVectorDB(config=mock_config)
    results = client.search(
        collection_name="exercises",
        query_vector=[0.1] * 1536,
        k=5,
        filter_conditions={"main_muscle_code": "CHEST"},
    )
    
    assert len(results) == 1
    assert results[0]["id"] == "test-id"
    assert results[0]["score"] == 0.95
    assert results[0]["payload"]["name"] == "Test Exercise"


def test_search_empty_results(mock_config, mock_qdrant_client):
    """Test search with no results."""
    # Setup mock
    mock_instance = mock_qdrant_client.return_value
    mock_instance.search.return_value = []
    
    client = QdrantVectorDB(config=mock_config)
    results = client.search(
        collection_name="exercises",
        query_vector=[0.1] * 1536,
        k=5,
    )
    
    assert len(results) == 0


def test_search_error_handling(mock_config, mock_qdrant_client):
    """Test search error handling."""
    # Setup mock to raise exception
    mock_instance = mock_qdrant_client.return_value
    mock_instance.search.side_effect = Exception("Search failed")
    
    client = QdrantVectorDB(config=mock_config)
    results = client.search(
        collection_name="exercises",
        query_vector=[0.1] * 1536,
        k=5,
    )
    
    # Should return empty list on error
    assert len(results) == 0


def test_upsert(mock_config, mock_qdrant_client):
    """Test upserting points."""
    # Setup mock
    mock_instance = mock_qdrant_client.return_value
    mock_result = Mock()
    mock_result.operation_id = "op-123"
    mock_instance.upsert.return_value = mock_result
    
    client = QdrantVectorDB(config=mock_config)
    
    from qdrant_client.models import PointStruct
    points = [
        PointStruct(id=1, vector=[0.1] * 1536, payload={"name": "Test"}),
    ]
    
    result = client.upsert(collection_name="exercises", points=points)
    
    assert result["status"] == "success"
    assert result["count"] == 1


def test_delete(mock_config, mock_qdrant_client):
    """Test deleting points."""
    mock_instance = mock_qdrant_client.return_value
    mock_instance.delete.return_value = Mock()
    
    client = QdrantVectorDB(config=mock_config)
    result = client.delete(collection_name="exercises", point_ids=["id1", "id2"])
    
    assert result["status"] == "success"
    assert result["count"] == 2

