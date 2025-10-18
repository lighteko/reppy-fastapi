"""Tests for RAG retriever."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.common import QdrantRetriever


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = Mock()
    config.embedding_model = "text-embedding-3-small"
    config.openai_api_key = "test-key"
    config.qdrant_search_k = 5
    config.qdrant_exercises_collection = "exercises"
    config.qdrant_memory_collection = "user_memory"
    return config


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    client = Mock()
    client.search = Mock(return_value=[])
    return client


@pytest.fixture
def mock_embeddings():
    """Mock embeddings model."""
    embeddings = Mock()
    embeddings.embed_query = Mock(return_value=[0.1] * 1536)
    return embeddings


@pytest.mark.asyncio
async def test_retriever_initialization(mock_config, mock_qdrant_client, mock_embeddings):
    """Test retriever initialization."""
    retriever = QdrantRetriever(
        qdrant_client=mock_qdrant_client,
        embeddings=mock_embeddings,
        config=mock_config,
    )
    
    assert retriever is not None
    assert retriever.qdrant == mock_qdrant_client
    assert retriever.embeddings == mock_embeddings


@pytest.mark.asyncio
async def test_retrieve_exercises(mock_config, mock_qdrant_client, mock_embeddings):
    """Test retrieving exercises."""
    # Setup mock search results
    mock_qdrant_client.search.return_value = [
        {
            "id": "ex1",
            "score": 0.95,
            "payload": {
                "name": "Barbell Bench Press",
                "exercise_code": "BARBELL_BENCH_PRESS",
                "source_id": "uuid-1",
                "main_muscle_id": "chest",
                "equipment_id": "barbell",
                "difficulty_level": 2,
            },
        },
    ]
    
    retriever = QdrantRetriever(
        qdrant_client=mock_qdrant_client,
        embeddings=mock_embeddings,
        config=mock_config,
    )
    
    documents = await retriever.retrieve_exercises(query="chest exercises", k=5)
    
    assert len(documents) == 1
    assert documents[0].page_content == "Barbell Bench Press"
    assert documents[0].metadata["exercise_code"] == "BARBELL_BENCH_PRESS"
    assert documents[0].metadata["score"] == 0.95


@pytest.mark.asyncio
async def test_retrieve_user_memory(mock_config, mock_qdrant_client, mock_embeddings):
    """Test retrieving user memory."""
    # Setup mock search results
    mock_qdrant_client.search.return_value = [
        {
            "id": "mem1",
            "score": 0.88,
            "payload": {
                "content": "User has a shoulder injury",
                "source_id": "uuid-mem1",
                "user_id": "user-123",
                "memory_type": "injury_note",
                "created_at": "2025-10-01T00:00:00Z",
            },
        },
    ]
    
    retriever = QdrantRetriever(
        qdrant_client=mock_qdrant_client,
        embeddings=mock_embeddings,
        config=mock_config,
    )
    
    documents = await retriever.retrieve_user_memory(
        query="shoulder problems",
        user_id="user-123",
        k=5,
    )
    
    assert len(documents) == 1
    assert documents[0].page_content == "User has a shoulder injury"
    assert documents[0].metadata["user_id"] == "user-123"
    assert documents[0].metadata["memory_type"] == "injury_note"


@pytest.mark.asyncio
async def test_retrieve_exercises_with_filters(mock_config, mock_qdrant_client, mock_embeddings):
    """Test retrieving exercises with filters."""
    retriever = QdrantRetriever(
        qdrant_client=mock_qdrant_client,
        embeddings=mock_embeddings,
        config=mock_config,
    )
    
    await retriever.retrieve_exercises(
        query="chest exercises",
        k=5,
        filters={"main_muscle_id": "chest"},
    )
    
    # Verify search was called with filters
    mock_qdrant_client.search.assert_called_once()
    call_kwargs = mock_qdrant_client.search.call_args[1]
    assert call_kwargs["filter_conditions"] == {"main_muscle_id": "chest"}


@pytest.mark.asyncio
async def test_retrieve_exercises_empty_results(mock_config, mock_qdrant_client, mock_embeddings):
    """Test retrieval with no results."""
    mock_qdrant_client.search.return_value = []
    
    retriever = QdrantRetriever(
        qdrant_client=mock_qdrant_client,
        embeddings=mock_embeddings,
        config=mock_config,
    )
    
    documents = await retriever.retrieve_exercises(query="nonexistent exercise", k=5)
    
    assert len(documents) == 0

