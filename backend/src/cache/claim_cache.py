"""Claim cache using RedisJSON."""

import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from loguru import logger

from ..config.settings import get_settings
from ..core.embeddings import EmbeddingManager
from ..core.redis_client import RedisClient
from ..models.verdict import Verdict


class ClaimCache:
    """Caches verified claims in Redis for fast retrieval."""

    def __init__(
        self,
        redis_client: RedisClient,
        embedding_manager: EmbeddingManager,
    ) -> None:
        """
        Initialize claim cache.

        Args:
            redis_client: Redis client instance
            embedding_manager: Embedding manager instance
        """
        self.redis = redis_client
        self.embeddings = embedding_manager
        self.settings = get_settings()
        logger.info("Claim cache initialized")

    def cache_verdict(
        self,
        claim_text: str,
        verdict: Verdict,
        citations: list = None,
        consensus_info: dict = None,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache verified claim with complete response data.

        Args:
            claim_text: Original claim text
            verdict: Verdict to cache
            citations: List of Citation objects (serializable)
            consensus_info: Consensus statistics dict
            ttl: Optional TTL in seconds
        """
        if ttl is None:
            ttl = self.settings.cache_ttl_seconds

        try:
            # Generate embedding for claim
            claim_vector = self.embeddings.embed_text(claim_text)

            # Serialize citations to dict format
            citations_data = []
            if citations:
                for citation in citations:
                    if hasattr(citation, 'model_dump'):
                        citations_data.append(citation.model_dump())
                    elif isinstance(citation, dict):
                        citations_data.append(citation)

            # Prepare quality metrics (ensure all values are primitives)
            quality_dict = {}
            if verdict.quality_metrics:
                for k, v in verdict.quality_metrics.items():
                    if v is not None:
                        quality_dict[k] = float(v) if isinstance(v, (int, float)) else str(v)

            # Redis HSET only accepts flat values (str, int, float, bytes).
            # Nested structures MUST be JSON-serialized into strings.
            cache_data = {
                "claim_text": claim_text,
                "claim_vector": claim_vector,
                "verdict": verdict.verdict_type.value,
                "confidence": float(verdict.confidence_score),
                "faithfulness": float(verdict.quality_metrics.get("faithfulness", 0.0)) if verdict.quality_metrics else 0.0,
                "verified_at": int(datetime.utcnow().timestamp()),
                "reasoning": verdict.reasoning_summary,
                "weighted_score": float(verdict.weighted_score),
                "consensus_percentage": float(verdict.consensus_percentage),
                # JSON-serialize complex nested data into strings
                "citations_json": json.dumps(citations_data, default=str),
                "consensus_info_json": json.dumps(consensus_info or {}, default=str),
                "quality_metrics_json": json.dumps(quality_dict, default=str),
            }

            # Store in Redis
            claim_id = f"claim_{uuid4().hex[:8]}"
            self.redis.add_verified_claim(claim_id, cache_data, ttl=ttl)

            logger.info(f"Cached verdict for claim: {claim_text[:50]}... (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Error caching verdict: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def get_cached_verdict(self, claim_text: str) -> Optional[dict]:
        """
        Get cached verdict for similar claim.

        Args:
            claim_text: Claim text to search for

        Returns:
            Cached verdict dict or None
        """
        try:
            # Generate query embedding
            query_vector = self.embeddings.embed_text(claim_text)

            # Search for similar claims with verdict-specific fields
            from ..config.constants import VERIFIED_CLAIMS_INDEX

            # Specify all fields we need from the verdict cache
            verdict_fields = [
                "claim_text", "verdict", "confidence", "faithfulness",
                "reasoning", "weighted_score", "consensus_percentage",
                "citations_json", "consensus_info_json", "quality_metrics_json",
            ]

            results = self.redis.vector_search(
                index_name=VERIFIED_CLAIMS_INDEX,
                vector_field="claim_vector",
                query_vector=query_vector,
                top_k=1,
                return_fields=verdict_fields,
            )

            if not results:
                return None

            # Check similarity threshold
            top_result = results[0]
            similarity = 1.0 - float(top_result.get("score", 1.0))  # Convert distance to similarity

            if similarity >= self.settings.cache_similarity_threshold:
                logger.info(f"Cache hit! Similarity: {similarity:.3f}")
                return top_result

            logger.info(f"Similar claim found but below threshold: {similarity:.3f} < {self.settings.cache_similarity_threshold}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving cached verdict: {e}")
            return None

