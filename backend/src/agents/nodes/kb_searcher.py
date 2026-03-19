"""Knowledge base searcher node - always searches KB first."""

from loguru import logger

from ...core.embeddings import EmbeddingManager
from ...core.redis_client import RedisClient
from ...models.state import GraphState
from ...retrieval.knowledge_base import KnowledgeBaseRetriever


class KBSearcherNode:
    """Searches knowledge base first before query planning."""

    def __init__(self, redis_client: RedisClient, embedding_manager: EmbeddingManager) -> None:
        """
        Initialize KB searcher.

        Args:
            redis_client: Redis client instance
            embedding_manager: Embedding manager instance
        """
        self.kb_retriever = KnowledgeBaseRetriever(redis_client, embedding_manager)
        logger.info("KB searcher node initialized")

    def search(self, state: GraphState) -> GraphState:
        """
        Search knowledge base first.

        Args:
            state: Current graph state

        Returns:
            Updated state with KB evidence
        """
        claim = state["claim"]
        
        # Get claim text (handle both Claim object and string)
        if hasattr(claim, 'normalized_text'):
            claim_text = claim.normalized_text
        elif isinstance(claim, str):
            claim_text = claim
        else:
            claim_text = str(claim)
        
        logger.info(f"🔍 Searching knowledge base for: {claim_text}")

        # Update progress
        state["current_step"] = "kb_search"
        state["progress_messages"].append({
            "step_id": 2,
            "label": "Knowledge Base Search",
            "detail": "Checking existing verified claims and knowledge",
        })

        try:
            # Search KB
            kb_evidence = self.kb_retriever.retrieve(claim_text)
            state["kb_evidence"] = kb_evidence

            if kb_evidence:
                # Calculate average relevance
                avg_relevance = sum([ev.relevance_score for ev in kb_evidence]) / len(kb_evidence)
                logger.info(f"✅ KB returned {len(kb_evidence)} results (avg relevance: {avg_relevance:.2f})")
                
                # Log top results
                for i, ev in enumerate(kb_evidence[:3], 1):
                    logger.info(f"   {i}. {ev.source.domain} (relevance: {ev.relevance_score:.2f})")
            else:
                logger.info(f"📭 KB returned no results - will use web search")

        except Exception as e:
            logger.error(f"❌ KB search error: {e}")
            state["kb_evidence"] = []

        return state

