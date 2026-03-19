"""Redis Stack unified client for vector search, caching, and JSON storage."""

import json
from typing import Any, Dict, List, Optional

import redis
from loguru import logger
from redis.commands.search.field import NumericField, TagField, TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from ..config.constants import (
    CACHE_PREFIX,
    KB_DOC_PREFIX,
    KNOWLEDGE_BASE_INDEX,
    VERIFIED_CLAIM_PREFIX,
    VERIFIED_CLAIMS_INDEX,
)
from ..config.settings import get_settings


class RedisClient:
    """Unified Redis Stack client for vector search, caching, and JSON storage."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        self.settings = get_settings()
        self.client = redis.from_url(
            self.settings.redis_url,
            decode_responses=True,
            encoding="utf-8",
        )
        logger.info(f"Redis client initialized: {self.settings.redis_host}:{self.settings.redis_port}")

        # Test connection
        self.client.ping()
        logger.info("Redis connection successful")

    def create_knowledge_base_index(self) -> None:
        """Create Redis Search index for knowledge base documents."""
        try:
            # Check if index exists
            self.client.ft(KNOWLEDGE_BASE_INDEX).info()
            logger.info(f"Index {KNOWLEDGE_BASE_INDEX} already exists")
            return
        except redis.ResponseError:
            pass

        # Define schema
        schema = [
            TextField("content", weight=1.0),
            VectorField(
                "content_vector",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.settings.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
            TagField("source"),
            TagField("category"),
            NumericField("timestamp", sortable=True),
            TextField("url"),
        ]

        # Create index
        self.client.ft(KNOWLEDGE_BASE_INDEX).create_index(
            schema,
            definition=IndexDefinition(prefix=[KB_DOC_PREFIX], index_type=IndexType.HASH),
        )
        logger.info(f"Created index: {KNOWLEDGE_BASE_INDEX}")

    def create_verified_claims_index(self) -> None:
        """Create Redis Search index for verified claims cache."""
        try:
            self.client.ft(VERIFIED_CLAIMS_INDEX).info()
            logger.info(f"Index {VERIFIED_CLAIMS_INDEX} already exists")
            return
        except redis.ResponseError:
            pass

        schema = [
            TextField("claim_text"),
            VectorField(
                "claim_vector",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.settings.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
            TagField("verdict"),
            NumericField("confidence", sortable=True),
            NumericField("faithfulness", sortable=True),
            NumericField("verified_at", sortable=True),
        ]

        self.client.ft(VERIFIED_CLAIMS_INDEX).create_index(
            schema,
            definition=IndexDefinition(prefix=[VERIFIED_CLAIM_PREFIX], index_type=IndexType.HASH),
        )
        logger.info(f"Created index: {VERIFIED_CLAIMS_INDEX}")

    def add_document(self, doc_id: str, doc_data: Dict[str, Any]) -> None:
        """
        Add document to knowledge base.

        Args:
            doc_id: Document ID (will be prefixed with KB_DOC_PREFIX)
            doc_data: Document data including content_vector
        """
        key = f"{KB_DOC_PREFIX}{doc_id}"

        # Convert vector to bytes for storage
        if "content_vector" in doc_data and isinstance(doc_data["content_vector"], list):
            import struct

            doc_data["content_vector"] = struct.pack(f"{len(doc_data['content_vector'])}f", *doc_data["content_vector"])

        self.client.hset(key, mapping=doc_data)

    def vector_search(
        self,
        index_name: str,
        vector_field: str,
        query_vector: List[float],
        top_k: int = 20,
        filters: Optional[str] = None,
        return_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            index_name: Index to search
            vector_field: Vector field name
            query_vector: Query embedding
            top_k: Number of results
            filters: Optional filter string
            return_fields: Optional list of fields to return (defaults to KB fields)

        Returns:
            List of search results
        """
        import struct

        # Convert vector to bytes (float32 little-endian)
        vec_bytes = struct.pack(f"{len(query_vector)}f", *query_vector)

        # Build query
        base_query = f"*=>[KNN {top_k} @{vector_field} $vector AS score]"
        if filters:
            base_query = f"({filters})=>[KNN {top_k} @{vector_field} $vector AS score]"

        # Use provided return_fields or default to knowledge base fields
        fields = return_fields or ["content", "source", "url", "category", "timestamp"]

        query = (
            Query(base_query)
            .return_fields("score", *fields)
            .sort_by("score")
            .dialect(2)
        )

        # Execute search
        results = self.client.ft(index_name).search(query, query_params={"vector": vec_bytes})

        # Parse results
        parsed_results = []
        for doc in results.docs:
            result = {
                "id": doc.id,
                "score": float(doc.score) if hasattr(doc, "score") else 0.0,
            }
            # Add all fields
            for key, value in doc.__dict__.items():
                if key not in ["id", "score", "payload"]:
                    result[key] = value
            parsed_results.append(result)

        return parsed_results

    def full_text_search(
        self,
        index_name: str,
        query_text: str,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Perform full-text search.

        Args:
            index_name: Index to search
            query_text: Search query
            top_k: Number of results

        Returns:
            List of search results
        """
        query = Query(query_text).paging(0, top_k).return_fields("content", "source", "url")

        results = self.client.ft(index_name).search(query)

        parsed_results = []
        for doc in results.docs:
            result = {"id": doc.id}
            for key, value in doc.__dict__.items():
                if key not in ["id", "payload"]:
                    result[key] = value
            parsed_results.append(result)

        return parsed_results

    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set cache value.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
        """
        cache_key = f"{CACHE_PREFIX}{key}"
        serialized = json.dumps(value)

        if ttl:
            self.client.setex(cache_key, ttl, serialized)
        else:
            self.client.set(cache_key, serialized)

    def cache_get(self, key: str) -> Optional[Any]:
        """
        Get cache value.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        cache_key = f"{CACHE_PREFIX}{key}"
        value = self.client.get(cache_key)

        if value:
            return json.loads(value)
        return None

    def cache_delete(self, key: str) -> None:
        """Delete cache key."""
        cache_key = f"{CACHE_PREFIX}{key}"
        self.client.delete(cache_key)

    def add_verified_claim(
        self,
        claim_id: str,
        claim_data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """
        Add verified claim to cache.

        Args:
            claim_id: Claim ID
            claim_data: Claim data including claim_vector
            ttl: Optional TTL in seconds
        """
        key = f"{VERIFIED_CLAIM_PREFIX}{claim_id}"

        # Convert vector to bytes
        if "claim_vector" in claim_data and isinstance(claim_data["claim_vector"], list):
            import struct

            claim_data["claim_vector"] = struct.pack(f"{len(claim_data['claim_vector'])}f", *claim_data["claim_vector"])

        self.client.hset(key, mapping=claim_data)

        if ttl:
            self.client.expire(key, ttl)

    def close(self) -> None:
        """Close Redis connection."""
        self.client.close()
        logger.info("Redis connection closed")

