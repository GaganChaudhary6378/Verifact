"""Evidence gatherer node - retrieves evidence from multiple sources."""

import asyncio
from typing import List
from uuid import uuid4

from loguru import logger

from ...config.constants import SourceCategory, StanceType
from ...core.embeddings import EmbeddingManager
from ...core.redis_client import RedisClient
from ...models.evidence import Evidence, Source
from ...models.state import GraphState
from ...retrieval.fact_checkers import FactCheckerRetriever
from ...retrieval.knowledge_base import KnowledgeBaseRetriever
from ...retrieval.reranker import CohereReranker
from ...retrieval.web_search import WebSearchRetriever
from ...scoring.credibility import CredibilityScorer
from ...scoring.stance_detector import StanceDetector


class EvidenceGathererNode:
    """Gathers evidence from multiple sources in parallel."""

    def __init__(
        self,
        redis_client: RedisClient,
        embedding_manager: EmbeddingManager,
    ) -> None:
        """
        Initialize evidence gatherer.

        Args:
            redis_client: Redis client instance
            embedding_manager: Embedding manager instance
        """
        self.kb_retriever = KnowledgeBaseRetriever(redis_client, embedding_manager)
        self.web_retriever = WebSearchRetriever()
        self.fact_checker_retriever = FactCheckerRetriever()
        self.reranker = CohereReranker()
        self.credibility_scorer = CredibilityScorer()
        self.stance_detector = StanceDetector()

        logger.info("Evidence gatherer node initialized")

    async def gather(self, state: GraphState) -> GraphState:
        """
        Gather evidence from multiple sources.

        Args:
            state: Current graph state

        Returns:
            Updated state with evidence
        """
        claim = state["claim"]
        query_plan = state["query_plan"]

        # Handle both Claim object and string
        if hasattr(claim, 'normalized_text'):
            claim_text = claim.normalized_text
        else:
            claim_text = str(claim)
        
        logger.info(f"Gathering evidence for: {claim_text}")

        # Update progress
        state["current_step"] = "evidence_gathering"
        state["progress_messages"].append({
            "step_id": 3,
            "label": "Evidence Gathering",
            "detail": "Retrieving information from multiple sources",
        })

        # Extract geo context if available
        geo_context = None
        if claim.context and "geo_data" in claim.context:
            geo_context = claim.context["geo_data"]

        # "First witness": treat the current page as evidence (validate if article supports the claim)
        current_page_evidence: List[Evidence] = []
        if getattr(claim, "context", None):
            ctx = claim.context
            page_meta = ctx.get("page_metadata") or {}
            webpage = ctx.get("webpage_content") or {}
            full_text = webpage.get("full_text", "")
            page_url = page_meta.get("url", "")
            page_title = page_meta.get("page_title", "Current Page") or "Current Page"
            if full_text and len(full_text) >= 50 and page_url and page_url.startswith("http"):
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(page_url).netloc.replace("www.", "") or "unknown"
                    content = full_text[:5000] if len(full_text) > 5000 else full_text
                    source = Source(
                        source_id=f"cur_{uuid4().hex[:8]}",
                        url=page_url,
                        domain=domain,
                        title=page_title[:500],
                        snippet=full_text[:500].strip(),
                        credibility_score=50.0,
                        category=SourceCategory.WEB_SEARCH,
                    )
                    ev = Evidence(
                        evidence_id=f"ev_cur_{uuid4().hex[:8]}",
                        source=source,
                        content=content,
                        relevance_score=1.0,
                        stance=StanceType.NEUTRAL,
                        stance_confidence=0.0,
                    )
                    current_page_evidence.append(ev)
                    logger.info("Added current page as first evidence")
                except Exception as e:
                    logger.warning(f"Failed to add current page evidence: {e}")

        # Gather from different sources in parallel
        tasks = []

        if query_plan["use_knowledge_base"]:
            # KB retrieval is sync, run in executor
            kb_task = asyncio.to_thread(
                self.kb_retriever.retrieve,
                claim,
                top_k=10,
            )
            tasks.append(("kb", kb_task))

        if query_plan["use_web_search"]:
            # Web retrieval is sync (Exa SDK), run in executor
            web_task = asyncio.to_thread(
                self.web_retriever.retrieve,
                claim,
                top_k=10,
                geo_context=geo_context,
            )
            tasks.append(("web", web_task))

        if query_plan["use_fact_checkers"]:
            # Fact-checker retrieval is sync (Exa SDK), run in executor
            fc_task = asyncio.to_thread(
                self.fact_checker_retriever.retrieve,
                claim,
                top_k=5,
            )
            tasks.append(("fact_check", fc_task))

        # Execute all tasks
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        # Parse results
        kb_evidence = []
        web_evidence = []
        fact_check_evidence = []

        for idx, (source_type, _) in enumerate(tasks):
            result = results[idx]
            if isinstance(result, Exception):
                logger.error(f"Error gathering {source_type} evidence: {result}")
                continue

            if source_type == "kb":
                kb_evidence = result
            elif source_type == "web":
                web_evidence = result
            elif source_type == "fact_check":
                fact_check_evidence = result

        # Combine all evidence (current page first, then KB, web, fact-check)
        all_evidence = current_page_evidence + kb_evidence + web_evidence + fact_check_evidence

        logger.info(
            f"Gathered evidence: KB={len(kb_evidence)}, "
            f"Web={len(web_evidence)}, FactCheck={len(fact_check_evidence)}"
        )

        # Update credibility scores
        for evidence in all_evidence:
            cred_data = self.credibility_scorer.score_url(str(evidence.source.url))
            evidence.source.credibility_score = cred_data["score"]
            evidence.source.category = cred_data["category"]
            evidence.source.bias = cred_data.get("bias")

        # Detect stance for all evidence
        logger.info("Detecting stance for evidence...")
        for evidence in all_evidence:
            stance, confidence = self.stance_detector.detect_stance(
                claim_text,
                evidence.content,
            )
            evidence.stance = stance
            evidence.stance_confidence = confidence

        # Rerank combined evidence
        logger.info("Reranking evidence...")
        reranked_evidence = self.reranker.rerank(
            claim_text,
            all_evidence,
            top_k=10,
        )

        # Update state
        state["kb_evidence"] = kb_evidence
        state["web_evidence"] = web_evidence
        state["fact_check_evidence"] = fact_check_evidence
        state["all_evidence"] = reranked_evidence

        logger.info(f"Final evidence count: {len(reranked_evidence)}")

        return state

    def gather_sync(self, state: GraphState) -> GraphState:
        """
        Synchronous wrapper for gather.

        Args:
            state: Current graph state

        Returns:
            Updated state
        """
        return asyncio.run(self.gather(state))

