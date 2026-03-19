"""Context refinement node - resolves ambiguous claims using page context and search tooling."""

from loguru import logger

from ...core.llm import LLMClient
from ...models.state import GraphState
from ...tools.context_search import ContextSearchTool


class ContextRefinementNode:
    """
    Resolves ambiguous claims (pronouns, 'the report', etc.) by searching
    the source page context and rewriting the claim to be self-contained.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client
        logger.info("Context refinement node initialized")

    def refine(self, state: GraphState) -> GraphState:
        """
        Enrich from page context: extract a context window and optionally rewrite
        the claim to be self-contained when it is ambiguous.
        """
        claim = state["claim"]
        if not claim:
            return state

        source_context = state.get("source_context") or {}
        webpage = source_context.get("webpage_content") or {}
        full_text = (webpage.get("full_text") or "").strip()

        if not full_text or len(full_text) < 50:
            logger.info("No sufficient page context for refinement; skipping")
            return state

        # Progress
        state["current_step"] = "context_refinement"
        state["progress_messages"].append({
            "step_id": 1,
            "label": "Context Refinement",
            "detail": "Using page content to enrich claim context",
        })

        tool = ContextSearchTool(full_text)
        claim_text = getattr(claim, "normalized_text", None) or getattr(claim, "original_text", "")

        # Always get a context window for downstream use (query planner, etc.)
        context_snippet = tool.get_window(claim_text, size=800)
        if not context_snippet and claim_text:
            matches = tool.search(claim_text[:50], window_size=300, max_results=1)
            if matches:
                context_snippet = matches[0].full_snippet
        if not context_snippet:
            context_snippet = full_text[:1500]
        context_snippet = tool.summarize_section(context_snippet, max_length=1200)
        state["source_context_snippet"] = context_snippet

        # Only rewrite claim when it was flagged ambiguous
        if not getattr(claim, "is_ambiguous", False):
            logger.info("Claim not ambiguous; enrichment snippet stored for downstream")
            return state

        # LLM: rewrite claim to be self-contained using the snippet
        system_prompt = """You are a fact-checking assistant. You are given a CLAIM that was highlighted on a webpage, and a CONTEXT snippet from that same webpage.

The claim may contain unclear references (e.g. "He resigned", "It was reported", "The study found"). Your job is to rewrite the claim so it is SELF-CONTAINED and clear, by filling in who/what from the context. Do not add information that is not in the context. If the context does not clarify, keep the claim as-is but minimal.

Respond with JSON only:
{ "refined_claim": "The rewritten, self-contained claim" }"""

        user_prompt = f"""Claim: "{claim_text}"

Context from the same page:
---
{context_snippet}
---

Output the refined claim as JSON."""

        try:
            response = self.llm.generate_json(system_prompt, user_prompt)
            refined = (response.get("refined_claim") or "").strip()
            if refined and refined != claim_text:
                claim = claim.model_copy(
                    update={"normalized_text": refined, "is_ambiguous": False}
                )
                state["claim"] = claim
                logger.info(f"Refined claim: {refined[:100]}...")
            else:
                logger.info("Refinement left claim unchanged or empty")
        except Exception as e:
            logger.warning(f"Context refinement error: {e}")

        return state
