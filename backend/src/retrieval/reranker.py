"""Cohere reranker for evidence reranking."""

from typing import List

import cohere
from loguru import logger

from ..config.settings import get_settings
from ..models.evidence import Evidence


class CohereReranker:
    """Reranks evidence using Cohere Rerank v3."""

    def __init__(self) -> None:
        """Initialize Cohere reranker."""
        self.settings = get_settings()
        self.api_key = self.settings.cohere_api_key

        if self.api_key:
            self.client = cohere.Client(self.api_key)
            logger.info("Cohere reranker initialized")
        else:
            self.client = None
            logger.warning("Cohere API key not configured, reranking disabled")

    def rerank(
        self,
        query: str,
        evidence_list: List[Evidence],
        top_k: int = 5,
    ) -> List[Evidence]:
        """
        Rerank evidence using Cohere.

        Args:
            query: Query text (claim)
            evidence_list: List of Evidence objects
            top_k: Number of top results to return

        Returns:
            Reranked evidence list
        """
        if not self.client or not evidence_list:
            return evidence_list[:top_k]

        try:
            # Prepare documents for reranking
            documents = [ev.content for ev in evidence_list]

            # Call Cohere Rerank API
            response = self.client.rerank(
                query=query,
                documents=documents,
                top_n=top_k,
                model="rerank-english-v3.0",
            )

            # Reorder evidence based on rerank results
            reranked_evidence = []
            for result in response.results:
                idx = result.index
                evidence = evidence_list[idx]
                # Update relevance score with rerank score
                evidence.relevance_score = result.relevance_score
                reranked_evidence.append(evidence)

            logger.info(f"Reranked {len(evidence_list)} → {len(reranked_evidence)} evidence items")
            return reranked_evidence

        except Exception as e:
            logger.error(f"Cohere reranking error: {e}")
            return evidence_list[:top_k]

