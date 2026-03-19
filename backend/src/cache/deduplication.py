"""Claim deduplication using semantic similarity."""

from typing import List

from loguru import logger

from ..core.embeddings import EmbeddingManager
from ..models.claim import Claim


class ClaimDeduplicator:
    """Detects duplicate or near-duplicate claims."""

    def __init__(self, embedding_manager: EmbeddingManager) -> None:
        """
        Initialize claim deduplicator.

        Args:
            embedding_manager: Embedding manager instance
        """
        self.embeddings = embedding_manager
        self.similarity_threshold = 0.95
        logger.info("Claim deduplicator initialized")

    def is_duplicate(self, claim1: Claim, claim2: Claim) -> bool:
        """
        Check if two claims are duplicates.

        Args:
            claim1: First claim
            claim2: Second claim

        Returns:
            True if duplicate
        """
        similarity = self.embeddings.compute_similarity(
            claim1.normalized_text,
            claim2.normalized_text,
        )

        is_dup = similarity >= self.similarity_threshold

        if is_dup:
            logger.info(f"Duplicate detected: {similarity:.3f} ≥ {self.similarity_threshold}")

        return is_dup

    def find_duplicates(self, claims: List[Claim]) -> List[List[int]]:
        """
        Find groups of duplicate claims.

        Args:
            claims: List of claims

        Returns:
            List of duplicate groups (indices)
        """
        if len(claims) < 2:
            return []

        # Compute pairwise similarities
        texts = [c.normalized_text for c in claims]
        similarity_matrix = self.embeddings.compute_similarity_matrix(texts)

        # Find duplicates
        duplicate_groups = []
        seen = set()

        for i in range(len(claims)):
            if i in seen:
                continue

            group = [i]
            for j in range(i + 1, len(claims)):
                if j in seen:
                    continue

                if similarity_matrix[i, j] >= self.similarity_threshold:
                    group.append(j)
                    seen.add(j)

            if len(group) > 1:
                duplicate_groups.append(group)

        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups

