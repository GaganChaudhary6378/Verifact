"""Knowledge base retriever using Redis VSS.

This module provides semantic search capabilities over a static knowledge base
using Redis Vector Similarity Search (VSS) with hybrid retrieval (dense + sparse).
"""

from typing import List, Optional
from uuid import uuid4

from loguru import logger

from ..config.constants import KNOWLEDGE_BASE_INDEX, SourceCategory, StanceType
from ..config.settings import get_settings
from ..core.embeddings import EmbeddingManager
from ..core.redis_client import RedisClient
from ..models.claim import Claim
from ..models.evidence import Evidence, Source


class KnowledgeBaseRetriever:
    """Retrieves evidence from static knowledge base using Redis VSS.
    
    Supports both dense (vector) and sparse (full-text) retrieval with
    Reciprocal Rank Fusion (RRF) for optimal results.
    """

    def __init__(
        self,
        redis_client: RedisClient,
        embedding_manager: EmbeddingManager,
    ) -> None:
        """Initialize knowledge base retriever.

        Args:
            redis_client: Redis client instance for vector search
            embedding_manager: Embedding manager for query encoding
        """
        self.redis = redis_client
        self.embeddings = embedding_manager
        self.settings = get_settings()
        logger.info("Knowledge base retriever initialized")

    def retrieve(
        self,
        claim: Claim,
        top_k: int = 20,
        filters: Optional[str] = None,
    ) -> List[Evidence]:
        """Retrieve relevant evidence from knowledge base using vector search.

        Args:
            claim: Claim to search for
            top_k: Number of results to retrieve
            filters: Optional Redis filter string (e.g., "@category:{academic}")

        Returns:
            List of Evidence objects ordered by relevance

        Raises:
            Exception: If retrieval fails critically
        """
        # Handle both Claim object and string
        claim_text = claim.normalized_text if hasattr(claim, 'normalized_text') else str(claim)
        logger.info(f"Retrieving KB evidence for: {claim_text[:80]}...")

        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_text(claim_text)

            # Perform vector search
            results = self.redis.vector_search(
                index_name=KNOWLEDGE_BASE_INDEX,
                vector_field="content_vector",
                query_vector=query_embedding,
                top_k=top_k,
                filters=filters,
            )

            # Convert to Evidence objects
            evidence_list = []
            for result in results:
                try:
                    evidence = self._result_to_evidence(result)
                    if evidence:
                        evidence_list.append(evidence)
                except Exception as e:
                    logger.warning(f"Error converting KB result to evidence: {e}")
                    continue

            logger.info(f"✓ Retrieved {len(evidence_list)} KB evidence items")
            return evidence_list

        except Exception as e:
            logger.error(f"Knowledge base retrieval failed: {e}")
            # Return empty list rather than crashing - graceful degradation
            return []

    def _result_to_evidence(self, result: dict) -> Optional[Evidence]:
        """Convert Redis search result to Evidence object.
        
        Args:
            result: Redis search result dictionary
            
        Returns:
            Evidence object or None if conversion fails
        """
        try:
            # Extract and validate data
            content = result.get("content", "")
            if not content or len(content) < 10:
                return None
            
            url = result.get("url", "http://localhost/kb")
            source_name = result.get("source", "knowledge_base")
            category_str = result.get("category", "academic")
            
            # Safely parse category
            try:
                category = SourceCategory(category_str)
            except ValueError:
                category = SourceCategory.ACADEMIC
            
            # Create Source
            source = Source(
                source_id=f"kb_{uuid4().hex[:8]}",
                url=url,
                domain=source_name,
                title=content[:100] + ("..." if len(content) > 100 else ""),
                snippet=content[:300] + ("..." if len(content) > 300 else ""),
                credibility_score=80.0,  # Default KB credibility
                category=category,
            )

            # Calculate relevance (convert distance to similarity)
            distance = float(result.get("score", 0.5))
            relevance = max(0.0, min(1.0, 1.0 - distance))

            # Create Evidence
            evidence = Evidence(
                evidence_id=f"ev_{uuid4().hex[:8]}",
                source=source,
                content=content[:2000],  # Limit content length
                relevance_score=relevance,
                stance=StanceType.NEUTRAL,  # Will be determined by stance detector
                stance_confidence=0.0,
            )

            return evidence
            
        except Exception as e:
            logger.debug(f"Failed to convert result to evidence: {e}")
            return None

    def hybrid_retrieve(
        self,
        claim: Claim,
        top_k: int = 20,
    ) -> List[Evidence]:
        """Perform hybrid retrieval using RRF (Reciprocal Rank Fusion).
        
        Combines dense (vector) and sparse (full-text) retrieval for better
        recall and precision.

        Args:
            claim: Claim to search for
            top_k: Number of final results to return

        Returns:
            List of Evidence objects ranked by RRF score
        """
        claim_text = claim.normalized_text if hasattr(claim, 'normalized_text') else str(claim)
        logger.info(f"Performing hybrid retrieval for: {claim_text[:80]}...")

        try:
            # 1. Dense retrieval (vector search)
            dense_results = self.retrieve(claim, top_k=top_k * 2)  # Get more for fusion

            # 2. Sparse retrieval (full-text search)
            sparse_results = []
            try:
                sparse_results_raw = self.redis.full_text_search(
                    index_name=KNOWLEDGE_BASE_INDEX,
                    query_text=claim_text,
                    top_k=top_k * 2,
                )

                # Convert sparse results to Evidence objects
                for result in sparse_results_raw:
                    evidence = self._result_to_evidence(result)
                    if evidence:
                        sparse_results.append(evidence)
                        
            except Exception as e:
                logger.warning(f"Full-text search failed, using only vector search: {e}")

            # 3. RRF Fusion
            if not sparse_results:
                # No sparse results, just return dense results
                logger.info(f"Hybrid retrieval (dense only): {len(dense_results)} results")
                return dense_results[:top_k]

            fused_results = self._apply_rrf_fusion(dense_results, sparse_results, top_k)
            
            logger.info(
                f"Hybrid retrieval complete: {len(dense_results)} dense + "
                f"{len(sparse_results)} sparse → {len(fused_results)} fused"
            )
            
            return fused_results

        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}")
            # Fallback to basic retrieval
            return self.retrieve(claim, top_k=top_k)

    def _apply_rrf_fusion(
        self,
        dense_results: List[Evidence],
        sparse_results: List[Evidence],
        top_k: int,
    ) -> List[Evidence]:
        """Apply Reciprocal Rank Fusion to combine retrieval results.
        
        Args:
            dense_results: Results from vector search
            sparse_results: Results from full-text search
            top_k: Number of results to return
            
        Returns:
            Fused and ranked evidence list
        """
        # Create rank mappings
        dense_ranks = {ev.evidence_id: rank + 1 for rank, ev in enumerate(dense_results)}
        sparse_ranks = {ev.evidence_id: rank + 1 for rank, ev in enumerate(sparse_results)}

        # Combine all unique evidence
        all_evidence_dict = {}
        for ev in dense_results:
            all_evidence_dict[ev.evidence_id] = ev
        for ev in sparse_results:
            if ev.evidence_id not in all_evidence_dict:
                all_evidence_dict[ev.evidence_id] = ev

        # Calculate RRF scores
        k = 60  # RRF constant (typical value)
        rrf_scores = {}
        
        for ev_id, ev in all_evidence_dict.items():
            dense_rank = dense_ranks.get(ev_id, float("inf"))
            sparse_rank = sparse_ranks.get(ev_id, float("inf"))

            # RRF formula: 1 / (k + rank)
            dense_score = 1.0 / (k + dense_rank) if dense_rank != float("inf") else 0.0
            sparse_score = 1.0 / (k + sparse_rank) if sparse_rank != float("inf") else 0.0

            # Weighted combination (dense gets higher weight for semantic search)
            rrf_scores[ev_id] = 0.7 * dense_score + 0.3 * sparse_score

        # Sort by RRF score and take top_k
        sorted_evidence = sorted(
            all_evidence_dict.values(),
            key=lambda ev: rrf_scores.get(ev.evidence_id, 0.0),
            reverse=True,
        )[:top_k]

        # Update relevance scores with normalized RRF scores
        max_score = max(rrf_scores.values()) if rrf_scores else 1.0
        for ev in sorted_evidence:
            normalized_score = rrf_scores.get(ev.evidence_id, 0.0) / max_score
            ev.relevance_score = max(0.0, min(1.0, normalized_score))

        return sorted_evidence

