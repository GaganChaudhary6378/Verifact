"""LangGraph workflow definition."""

from langgraph.graph import END, StateGraph
from loguru import logger

from ..core.embeddings import EmbeddingManager
from ..core.llm import LLMClient
from ..core.redis_client import RedisClient
from ..models.state import GraphState
from .nodes.claim_processor import ClaimProcessorNode
from .nodes.context_refinement import ContextRefinementNode
from .nodes.evidence_gatherer import EvidenceGathererNode
from .nodes.kb_searcher import KBSearcherNode
from .nodes.query_planner import QueryPlannerNode
from .nodes.verdict_synthesizer import VerdictSynthesizerNode


def create_verification_graph(
    redis_client: RedisClient,
    embedding_manager: EmbeddingManager,
    llm_client: LLMClient,
) -> StateGraph:
    """
    Create LangGraph verification workflow.

    Flow:
    1. Claim Processor - Normalize and extract entities
    2. KB Searcher - Search knowledge base FIRST (always)
    3. Query Planner - Decide if web search needed based on KB results
    4. Evidence Gatherer - Gather from web/fact-checkers if needed
    5. Verdict Synthesizer - Generate final verdict

    Args:
        redis_client: Redis client instance
        embedding_manager: Embedding manager instance
        llm_client: LLM client instance

    Returns:
        Compiled state graph
    """
    logger.info("Creating verification graph")

    # Initialize nodes
    claim_processor = ClaimProcessorNode(llm_client)
    context_refinement = ContextRefinementNode(llm_client)
    kb_searcher = KBSearcherNode(redis_client, embedding_manager)
    query_planner = QueryPlannerNode(llm_client)
    evidence_gatherer = EvidenceGathererNode(redis_client, embedding_manager)
    verdict_synthesizer = VerdictSynthesizerNode(llm_client)

    # Create graph
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("claim_processor", claim_processor.process)
    workflow.add_node("context_refinement", context_refinement.refine)
    workflow.add_node("kb_searcher", kb_searcher.search)
    workflow.add_node("query_planner", query_planner.plan)
    workflow.add_node("evidence_gatherer", evidence_gatherer.gather_sync)
    workflow.add_node("verdict_synthesizer", verdict_synthesizer.synthesize)

    # Edges: claim_processor -> (context_refinement if ambiguous else kb_searcher) -> kb_searcher -> ...
    workflow.set_entry_point("claim_processor")
    workflow.add_conditional_edges(
        "claim_processor",
        _route_after_claim_processor,
        {"context_refinement": "context_refinement", "kb_searcher": "kb_searcher"},
    )
    workflow.add_edge("context_refinement", "kb_searcher")
    workflow.add_edge("kb_searcher", "query_planner")
    workflow.add_edge("query_planner", "evidence_gatherer")
    workflow.add_edge("evidence_gatherer", "verdict_synthesizer")
    workflow.add_edge("verdict_synthesizer", END)

    # Compile graph
    graph = workflow.compile()

    logger.info("Verification graph created successfully")
    logger.info("Flow: Claim → [Context Refinement if ambiguous] → KB Search → Query Plan → Evidence → Verdict")
    return graph


def _route_after_claim_processor(state: GraphState) -> str:
    """Route to context_refinement if claim is ambiguous or we have substantial page content to enrich from."""
    claim = state.get("claim")
    if not claim:
        return "kb_searcher"
    if getattr(claim, "is_ambiguous", False):
        return "context_refinement"
    source_context = state.get("source_context") or {}
    webpage = source_context.get("webpage_content") or {}
    full_text = (webpage.get("full_text") or "").strip()
    if len(full_text) >= 200:
        return "context_refinement"
    return "kb_searcher"


def should_use_cache(state: GraphState) -> str:
    """
    Conditional edge: Check if cached result exists.

    Args:
        state: Current state

    Returns:
        Next node name ("cached" if found, "claim_processor" if not)
    """
    from ..cache.claim_cache import ClaimCache
    from ..core.embeddings import EmbeddingManager
    from ..core.redis_client import RedisClient

    try:
        # Get components from state (they should be available in the graph context)
        # For now, we'll check cache in the API layer, so this always goes to claim_processor
        # The actual cache check happens in main.py before invoking the graph
        raw_claim = state.get("raw_claim", "")
        if not raw_claim:
            return "claim_processor"

        # Note: Cache check is actually done in main.py before graph invocation
        # This function is kept for future conditional routing in the graph
        return "claim_processor"
    except Exception as e:
        logger.warning(f"Error checking cache: {e}")
        return "claim_processor"


def should_retry(state: GraphState) -> str:
    """
    Conditional edge: Check if should retry with different strategy.

    Args:
        state: Current state

    Returns:
        Next node name
    """
    if state.get("error"):
        logger.warning("Error in state, ending workflow")
        return END

    return END

