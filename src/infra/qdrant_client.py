"""Qdrant Vector DB client with health checks and query APIs."""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SearchRequest,
    VectorParams,
)
from loguru import logger

from src.config import get_config


class QdrantVectorDB:
    """Wrapper around Qdrant client with health checks and query utilities."""
    
    def __init__(self, config: Optional[Any] = None):
        """Initialize Qdrant client.
        
        Args:
            config: Configuration object. If None, uses get_config().
        """
        self.config = config or get_config()
        
        # Initialize client based on configuration
        if self.config.qdrant_grpc:
            self.client = QdrantClient(
                url=self.config.qdrant_url,
                api_key=self.config.qdrant_api_key,
                prefer_grpc=True,
            )
        else:
            self.client = QdrantClient(
                url=self.config.qdrant_url,
                api_key=self.config.qdrant_api_key,
            )
        
        logger.info(f"Initialized Qdrant client: {self.config.qdrant_url}")
    
    def health(self) -> Dict[str, Any]:
        """Check Qdrant server health.
        
        Returns:
            Dict containing health status and collection info.
        """
        try:
            collections = self.client.get_collections()
            return {
                "status": "healthy",
                "collections": [c.name for c in collections.collections],
                "url": self.config.qdrant_url,
            }
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "url": self.config.qdrant_url,
            }
    
    def upsert(
        self,
        collection_name: str,
        points: List[PointStruct],
    ) -> Dict[str, Any]:
        """Upsert points into a collection.
        
        Args:
            collection_name: Name of the collection.
            points: List of PointStruct objects to upsert.
            
        Returns:
            Dict with operation status.
        """
        try:
            result = self.client.upsert(
                collection_name=collection_name,
                points=points,
            )
            logger.info(f"Upserted {len(points)} points to {collection_name}")
            return {
                "status": "success",
                "collection": collection_name,
                "count": len(points),
                "operation_id": result.operation_id if hasattr(result, 'operation_id') else None,
            }
        except Exception as e:
            logger.error(f"Upsert failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        k: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in a collection.
        
        Args:
            collection_name: Name of the collection to search.
            query_vector: Query embedding vector.
            k: Number of results to return.
            filter_conditions: Optional filter conditions (field -> value mapping).
            score_threshold: Optional minimum score threshold.
            
        Returns:
            List of search results with payload and score.
        """
        try:
            # Build filter if conditions provided
            query_filter = None
            if filter_conditions:
                must_conditions = []
                for field, value in filter_conditions.items():
                    must_conditions.append(
                        FieldCondition(
                            key=field,
                            match=MatchValue(value=value),
                        )
                    )
                query_filter = Filter(must=must_conditions)
            
            # Execute search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=k,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": str(result.id),
                    "score": result.score,
                    "payload": result.payload,
                })
            
            logger.info(f"Search returned {len(formatted_results)} results from {collection_name}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def delete(
        self,
        collection_name: str,
        point_ids: List[Union[str, UUID, int]],
    ) -> Dict[str, Any]:
        """Delete points from a collection.
        
        Args:
            collection_name: Name of the collection.
            point_ids: List of point IDs to delete.
            
        Returns:
            Dict with operation status.
        """
        try:
            result = self.client.delete(
                collection_name=collection_name,
                points_selector=point_ids,
            )
            logger.info(f"Deleted {len(point_ids)} points from {collection_name}")
            return {
                "status": "success",
                "collection": collection_name,
                "count": len(point_ids),
            }
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def create_collection_if_not_exists(
        self,
        collection_name: str,
        vector_size: int,
        distance: str = "Cosine",
    ) -> bool:
        """Create a collection if it doesn't exist.
        
        Args:
            collection_name: Name of the collection to create.
            vector_size: Size of the vectors.
            distance: Distance metric (Cosine, Euclid, Dot).
            
        Returns:
            True if collection was created or already exists.
        """
        try:
            collections = self.client.get_collections()
            existing_names = [c.name for c in collections.collections]
            
            if collection_name in existing_names:
                logger.info(f"Collection {collection_name} already exists")
                return True
            
            # Map distance string to enum
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclid": Distance.EUCLID,
                "Dot": Distance.DOT,
            }
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_map.get(distance, Distance.COSINE),
                ),
            )
            logger.info(f"Created collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

