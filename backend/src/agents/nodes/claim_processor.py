"""Claim processor node - extracts, normalizes, and classifies claims."""

import re
from typing import List
from uuid import uuid4

from loguru import logger

from ...config.constants import ClaimType
from ...core.llm import LLMClient
from ...models.claim import Claim, Entity, SubClaim
from ...models.state import GraphState


class ClaimProcessorNode:
    """Processes raw claim text into structured Claim object."""

    def __init__(self, llm_client: LLMClient) -> None:
        """
        Initialize claim processor.

        Args:
            llm_client: LLM client instance
        """
        self.llm = llm_client
        logger.info("Claim processor node initialized")

    def normalize_text(self, text: str) -> str:
        """
        Normalize claim text.

        Args:
            text: Raw claim text

        Returns:
            Normalized text
        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Remove URLs
        text = re.sub(r"http\S+|www.\S+", "", text)

        # Remove special characters (keep basic punctuation)
        text = re.sub(r"[^\w\s.,!?-]", "", text)

        return text

    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract named entities from text using LLM.

        Args:
            text: Input text

        Returns:
            List of Entity objects
        """
        system_prompt = """You are a named entity recognition expert. Extract all important named entities from the text.

Entity types to identify:
- PERSON: People's names
- ORG: Organizations, companies, institutions
- GPE: Countries, cities, states (geopolitical entities)
- DATE: Dates or time periods
- MONEY: Monetary values
- PERCENT: Percentages
- PRODUCT: Products, brands
- EVENT: Named events

Respond in JSON format:
{
    "entities": [
        {"text": "entity text", "type": "PERSON"},
        {"text": "another entity", "type": "ORG"}
    ]
}

If no entities found, return empty list."""

        user_prompt = f"Extract entities from: {text}"

        try:
            response = self.llm.generate_json(system_prompt, user_prompt)
            entities_data = response.get("entities", [])

            entities = []
            for ent_data in entities_data:
                entity = Entity(
                    text=ent_data.get("text", ""),
                    type=ent_data.get("type", "UNKNOWN"),
                    start=0,  # LLM doesn't provide exact positions
                    end=0,
                )
                entities.append(entity)

            return entities
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return []

    def classify_claim(self, text: str) -> ClaimType:
        """
        Classify claim type using LLM.

        Args:
            text: Claim text

        Returns:
            ClaimType
        """
        system_prompt = """You are a claim classification expert. Classify the given claim into ONE of these types:
- factual: Objective facts that can be verified
- statistical: Claims involving numbers, percentages, or statistics
- event: Claims about past or current events
- prediction: Claims about future events
- opinion: Subjective opinions or beliefs

Respond with ONLY the type name, nothing else."""

        user_prompt = f"Classify this claim: {text}"

        try:
            response = self.llm.generate_text(system_prompt, user_prompt)
            response = response.strip().lower()

            # Map response to ClaimType
            type_map = {
                "factual": ClaimType.FACTUAL,
                "statistical": ClaimType.STATISTICAL,
                "event": ClaimType.EVENT,
                "prediction": ClaimType.PREDICTION,
                "opinion": ClaimType.OPINION,
            }

            return type_map.get(response, ClaimType.FACTUAL)
        except Exception as e:
            logger.error(f"Claim classification error: {e}")
            return ClaimType.FACTUAL

    def decompose_claim(self, text: str) -> List[SubClaim]:
        """
        Decompose complex claim into sub-claims.

        Args:
            text: Claim text

        Returns:
            List of SubClaim objects
        """
        system_prompt = """You are a claim decomposition expert. Break down complex claims into simpler sub-claims that can be verified independently.

If the claim is simple, return it as-is. If complex, split it into 2-4 sub-claims.

Respond in JSON format:
{
    "sub_claims": [
        {"text": "sub-claim 1", "priority": 1},
        {"text": "sub-claim 2", "priority": 2}
    ]
}

Priority: 1=high (core claim), 2=medium, 3=low (supporting detail)"""

        user_prompt = f"Decompose this claim: {text}"

        try:
            response = self.llm.generate_json(system_prompt, user_prompt)
            sub_claims_data = response.get("sub_claims", [])

            sub_claims = []
            for sc_data in sub_claims_data:
                sub_claim = SubClaim(
                    text=sc_data.get("text", ""),
                    claim_type=ClaimType.FACTUAL,  # Simplified
                    priority=sc_data.get("priority", 1),
                )
                sub_claims.append(sub_claim)

            return sub_claims
        except Exception as e:
            logger.error(f"Claim decomposition error: {e}")
            # Return original as single sub-claim
            return [SubClaim(text=text, claim_type=ClaimType.FACTUAL, priority=1)]

    def _detect_ambiguity(self, claim_text: str) -> bool:
        """
        Detect if the claim has unresolved references (pronouns, 'the report', etc.)
        that need page context to resolve.

        Args:
            claim_text: Raw claim text.

        Returns:
            True if claim is ambiguous and would benefit from context refinement.
        """
        system_prompt = """You are an expert at judging if a short claim needs more context to be verified.

A claim is AMBIGUOUS (needs context) if:
- The MAIN SUBJECT is a pronoun (he, she, it, they) and is never named in the claim. Example: "He investigated buying a firm" is ambiguous even if the claim later names other people (e.g. "Herb Rawdon")—we still do not know who "he" is.
- It uses vague references for the subject: "the report said", "the study found", "the company announced", "the minister stated".
- It refers to "the incident", "the decision", "yesterday's announcement" without saying what/when.

A claim is NOT ambiguous only if the main actor/source is explicitly named (e.g. "John Smith resigned" or "Reuters reported that...").

Respond in JSON only:
{ "is_ambiguous": true or false, "reason": "one short phrase" }"""

        user_prompt = f'Claim: "{claim_text}"'

        try:
            response = self.llm.generate_json(system_prompt, user_prompt)
            return bool(response.get("is_ambiguous", False))
        except Exception as e:
            logger.warning(f"Ambiguity detection error: {e}")
            return False

    def process(self, state: GraphState) -> GraphState:
        """
        Process claim from state.

        Args:
            state: Current graph state

        Returns:
            Updated state
        """
        raw_claim = state["raw_claim"]
        logger.info(f"Processing claim: {raw_claim}")

        # Update progress
        state["current_step"] = "claim_processing"
        state["progress_messages"].append({
            "step_id": 1,
            "label": "Claim Processing",
            "detail": "Normalizing and analyzing claim structure",
        })

        # Normalize
        normalized_text = self.normalize_text(raw_claim)

        # Extract entities
        entities = self.extract_entities(raw_claim)

        # Classify
        claim_type = self.classify_claim(normalized_text)

        # Decompose
        sub_claims = self.decompose_claim(normalized_text)

        # Detect if claim needs context refinement (unresolved refs: he, she, it, the report, etc.)
        is_ambiguous = self._detect_ambiguity(raw_claim)

        # Create Claim object
        claim = Claim(
            claim_id=f"claim_{uuid4().hex[:8]}",
            original_text=raw_claim,
            normalized_text=normalized_text,
            claim_type=claim_type,
            entities=entities,
            sub_claims=sub_claims,
            context=state.get("source_context"),
            is_ambiguous=is_ambiguous,
        )

        state["claim"] = claim
        logger.info(f"Claim processed: type={claim_type}, entities={len(entities)}, sub_claims={len(sub_claims)}")

        return state

