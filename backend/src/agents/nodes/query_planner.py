"""Query planner node - decides retrieval strategy."""

from loguru import logger

from ...core.llm import LLMClient
from ...models.state import GraphState


class QueryPlannerNode:
    """Plans retrieval strategy based on claim type and context."""

    def __init__(self, llm_client: LLMClient) -> None:
        """
        Initialize query planner.

        Args:
            llm_client: LLM client instance
        """
        self.llm = llm_client
        logger.info("Query planner node initialized")

    def plan(self, state: GraphState) -> GraphState:
        """
        Plan retrieval strategy.

        Args:
            state: Current graph state

        Returns:
            Updated state with query plan
        """
        claim = state["claim"]
        
        # Handle both Claim object and string
        if hasattr(claim, 'normalized_text'):
            claim_text = claim.normalized_text
            claim_type = getattr(claim, 'claim_type', 'FACTUAL')
            entities = getattr(claim, 'entities', [])
        else:
            claim_text = str(claim)
            claim_type = 'FACTUAL'
            entities = []
        
        logger.info(f"Planning query for: {claim_text}")

        # Update progress
        state["current_step"] = "query_planning"
        state["progress_messages"].append({
            "step_id": 2,
            "label": "Query Planning",
            "detail": f"Analyzing claim type and determining search strategy",
        })

        system_prompt = """You are a search strategy expert. Based on the claim and KB search results, decide the retrieval strategy.

Output JSON:
{
    "use_web_search": true/false,
    "use_fact_checkers": true/false,
    "search_queries": ["query1", "query2", "query3"],
    "reasoning": "brief explanation"
}

CRITICAL RULES:
1. If KB returned relevant results (similarity > 0.8): use_web_search=false
2. If KB returned some results (similarity 0.6-0.8): use_web_search=true (to verify)
3. If KB returned no/poor results (similarity < 0.6): use_web_search=true (primary source)

For WEB SEARCH strategy:
- Current events/news: use_web_search=true, use_fact_checkers=true
- Scientific/technical: use_web_search=true
- Political claims: use_web_search=true, use_fact_checkers=true

Always generate 2-4 diverse search queries for better coverage.
"""

        # Get KB search summary from state
        kb_evidence = state.get("kb_evidence", [])
        kb_summary = f"KB returned {len(kb_evidence)} results"
        if kb_evidence:
            avg_score = sum([ev.relevance_score for ev in kb_evidence]) / len(kb_evidence)
            kb_summary += f" (avg relevance: {avg_score:.2f})"

        # Use enriched context snippet from context_refinement when available
        context_snippet = state.get("source_context_snippet") or ""
        context_block = ""
        if context_snippet:
            context_block = f"\nRelevant excerpt from the source page:\n---\n{context_snippet[:600]}\n---\n"

        user_prompt = f"""Claim: {claim_text}
Claim Type: {claim_type}
Entities: {[e.text if hasattr(e, 'text') else str(e) for e in entities]}
Knowledge Base Search: {kb_summary}{context_block}

Plan the retrieval strategy. If KB has good results, we may not need web search. Use the source page excerpt to inform more specific search queries when relevant."""

        try:
            logger.info(f"🔍 Query planner input - Claim: {claim_text[:100]}...")
            logger.info(f"🔍 Claim type: {claim_type}, Entities: {len(entities)}")
            logger.info(f"🔍 KB search already done: {len(kb_evidence)} results")
            
            response = self.llm.generate_json(system_prompt, user_prompt)
            logger.info(f"📋 LLM response: {response}")

            # Create query plan - KB search already done, now decide on web search
            query_plan = {
                "use_knowledge_base": False,  # Already searched
                "use_web_search": response.get("use_web_search", True),  # Default True
                "use_fact_checkers": response.get("use_fact_checkers", False),
                "search_queries": response.get("search_queries", [claim_text]),
                "reasoning": response.get("reasoning", ""),
            }

            state["query_plan"] = query_plan
            logger.info(f"✅ Query plan created:")
            logger.info(f"   - Knowledge Base: {query_plan['use_knowledge_base']}")
            logger.info(f"   - Web Search: {query_plan['use_web_search']}")
            logger.info(f"   - Fact Checkers: {query_plan['use_fact_checkers']}")
            logger.info(f"   - Queries: {query_plan['search_queries']}")
            logger.info(f"   - Reasoning: {query_plan['reasoning']}")

        except Exception as e:
            logger.error(f"❌ Query planning error: {e}")
            # Default plan: use web search (KB already searched)
            state["query_plan"] = {
                "use_knowledge_base": False,  # Already done
                "use_web_search": True,
                "use_fact_checkers": True,
                "search_queries": [claim.normalized_text],
                "reasoning": "Default strategy - web search (KB already checked)",
            }
            logger.info(f"Using default plan (web search priority)")

        return state

