"""Verdict synthesizer node - generates final verdict."""

import re
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from ...config.constants import VerdictType
from ...core.llm import LLMClient
from ...models.state import GraphState
from ...models.verdict import Verdict
from ...scoring.consensus import ConsensusCalculator
from ...scoring.thresholds import ThresholdEvaluator
from ..prompts import create_verdict_prompt


class VerdictSynthesizerNode:
    """Synthesizes final verdict from evidence and consensus."""

    def __init__(self, llm_client: LLMClient) -> None:
        """
        Initialize verdict synthesizer.

        Args:
            llm_client: LLM client instance
        """
        self.llm = llm_client
        self.consensus_calculator = ConsensusCalculator()
        self.threshold_evaluator = ThresholdEvaluator()
        logger.info("Verdict synthesizer node initialized")

    def synthesize(self, state: GraphState) -> GraphState:
        """
        Synthesize final verdict.

        Args:
            state: Current graph state

        Returns:
            Updated state with verdict
        """
        claim = state["claim"]
        all_evidence = state["all_evidence"]

        # Handle both Claim object and string
        if hasattr(claim, 'normalized_text'):
            claim_text = claim.normalized_text
        else:
            claim_text = str(claim)
        
        logger.info(f"Synthesizing verdict for: {claim_text}")

        # Update progress
        state["current_step"] = "verdict_synthesis"
        state["progress_messages"].append({
            "step_id": 4,
            "label": "Verdict Synthesis",
            "detail": "Analyzing evidence and calculating consensus",
        })

        # Calculate consensus
        consensus_result = self.consensus_calculator.calculate(all_evidence)
        state["consensus_result"] = consensus_result

        # Evaluate thresholds
        verdict_type = self.threshold_evaluator.evaluate(consensus_result)
        confidence_score = self.threshold_evaluator.get_confidence_score(consensus_result)

        # Generate reasoning summary using LLM
        reasoning_summary = self._generate_reasoning(claim, all_evidence, verdict_type, consensus_result)

        # Create verdict object
        verdict = Verdict(
            verdict_type=verdict_type,
            confidence_score=confidence_score,
            weighted_score=consensus_result["weighted_score"],
            consensus_percentage=consensus_result["consensus_percentage"],
            reasoning_summary=reasoning_summary,
            evidence_used=all_evidence[:5],  # Top 5 evidence
            quality_metrics=None,  # Will be added by evaluation layer
        )

        state["verdict"] = verdict

        logger.info(
            f"Verdict: {verdict_type}, "
            f"confidence={confidence_score:.2f}, "
            f"score={consensus_result['weighted_score']:.2f}"
        )

        return state

    def _generate_reasoning(
        self,
        claim,
        evidence_list,
        verdict_type: VerdictType,
        consensus_result: dict,
    ) -> str:
        """
        Generate human-readable reasoning summary using RAGAS-optimized prompt.

        Args:
            claim: Claim object or string
            evidence_list: List of evidence
            verdict_type: Determined verdict
            consensus_result: Consensus calculation result

        Returns:
            Reasoning summary string with inline citations
        """
        # Handle both Claim object and string
        if hasattr(claim, 'normalized_text'):
            claim_text = claim.normalized_text
        else:
            claim_text = str(claim)
        
        try:
            # Create RAGAS-optimized prompt with full evidence metadata
            prompt = create_verdict_prompt(claim_text, evidence_list[:10])
            
            logger.debug("Generating RAGAS-optimized verdict reasoning")
            
            # Generate structured verdict response with LOW TEMPERATURE
            # Lower temperature = more deterministic, less creative, less hallucination
            system_prompt = """You are a fact-checking expert. Follow the instructions exactly and provide a structured verdict analysis.
You MUST cite evidence using [Source N] format for every statement.
Do NOT add information not present in the provided evidence.
EXTRACT direct quotes - DO NOT paraphrase or add context."""
            
            # Use custom LLM invocation with low temperature for faithfulness
            
            # Create a low-temperature LLM instance for verdict generation
            faithful_llm = ChatOpenAI(
                model=self.llm.settings.primary_llm,
                api_key=self.llm.settings.openai_api_key,
                temperature=0.1,  # Very low temperature for deterministic output
                max_tokens=800,   # Limit to prevent over-elaboration
            )
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ]
            
            response = faithful_llm.invoke(messages)
            reasoning = response.content
            
            # Parse and validate structured output
            parsed_reasoning = self._parse_structured_verdict(reasoning)
            
            if parsed_reasoning:
                # Ensure it fits within the 1000 character limit
                truncated = self._truncate_reasoning(parsed_reasoning, max_length=980)
                logger.info("Successfully generated structured verdict with citations")
                return truncated
            else:
                # If parsing fails, return raw output (it may still be good)
                logger.warning("Could not parse structured sections, using raw output")
                truncated = self._truncate_reasoning(reasoning.strip(), max_length=980)
                return truncated
                
        except Exception as e:
            logger.error(f"RAGAS reasoning generation error: {e}")
            # Fallback to evidence-grounded reasoning
            return self._create_fallback_reasoning(
                claim_text, evidence_list, verdict_type, consensus_result
            )
    
    def _truncate_reasoning(self, reasoning: str, max_length: int = 980) -> str:
        """
        Intelligently truncate reasoning to fit within character limit.
        
        Preserves complete sentences and citations while staying under limit.
        
        Args:
            reasoning: Full reasoning text
            max_length: Maximum allowed characters
            
        Returns:
            Truncated reasoning that fits within limit
        """
        if len(reasoning) <= max_length:
            return reasoning
        
        # Try to truncate at sentence boundary
        truncated = reasoning[:max_length]
        
        # Find last complete sentence (ending with . ! ?)
        last_period = max(
            truncated.rfind('. '),
            truncated.rfind('! '),
            truncated.rfind('? ')
        )
        
        if last_period > max_length * 0.7:  # At least 70% of content preserved
            truncated = truncated[:last_period + 1]
        else:
            # No good sentence boundary, truncate at word boundary
            last_space = truncated.rfind(' ')
            if last_space > 0:
                truncated = truncated[:last_space] + "..."
        
        logger.warning(
            f"Reasoning truncated from {len(reasoning)} to {len(truncated)} characters"
        )
        return truncated
    
    def _parse_structured_verdict(self, llm_output: str) -> str:
        """
        Parse structured verdict output and format for display.
        
        Extracts VERDICT, CONFIDENCE, EXPLANATION, KEY_EVIDENCE, and REASONING
        sections and combines them into a coherent summary.
        
        Args:
            llm_output: Raw LLM output with structured sections
            
        Returns:
            Formatted reasoning summary, or None if parsing fails
        """
        try:
            # Extract main sections using regex
            explanation_match = re.search(
                r'3\.\s*EXPLANATION:\s*(.+?)(?=4\.\s*KEY_EVIDENCE:|5\.\s*REASONING:|$)',
                llm_output,
                re.DOTALL | re.IGNORECASE
            )
            
            key_evidence_match = re.search(
                r'4\.\s*KEY_EVIDENCE:\s*(.+?)(?=5\.\s*REASONING:|$)',
                llm_output,
                re.DOTALL | re.IGNORECASE
            )
            
            reasoning_match = re.search(
                r'5\.\s*REASONING:\s*(.+?)$',
                llm_output,
                re.DOTALL | re.IGNORECASE
            )
            
            # Build formatted output
            parts = []
            
            if explanation_match:
                explanation = explanation_match.group(1).strip()
                parts.append(explanation)
            
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
                if reasoning and reasoning not in parts:
                    parts.append(reasoning)
            
            if key_evidence_match:
                key_evidence = key_evidence_match.group(1).strip()
                # Only add key evidence if it's not already mentioned
                if key_evidence and len(key_evidence) < 500:
                    parts.append(f"Key Evidence: {key_evidence}")
            
            if parts:
                return " ".join(parts)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing structured verdict: {e}")
            return None
    
    def _create_fallback_reasoning(
        self,
        claim_text: str,
        evidence_list,
        verdict_type: VerdictType,
        consensus_result: dict,
    ) -> str:
        """
        Create fallback reasoning that still adheres to faithfulness principles.
        
        Args:
            claim_text: The claim being verified
            evidence_list: List of evidence
            verdict_type: Determined verdict
            consensus_result: Consensus calculation result
            
        Returns:
            Evidence-grounded fallback reasoning
        """
        # Build reasoning from evidence facts only
        source_count = len(evidence_list)
        avg_credibility = (
            sum(ev.source.credibility_score for ev in evidence_list[:5]) / min(5, source_count)
            if source_count > 0
            else 0
        )
        
        # Count supporting vs refuting evidence
        supporting = sum(1 for ev in evidence_list if ev.stance.value == "supports")
        refuting = sum(1 for ev in evidence_list if ev.stance.value == "refutes")
        
        reasoning_parts = [
            f"Based on analysis of {source_count} sources "
            f"(average credibility: {avg_credibility:.0f}/100), "
            f"the claim is classified as {verdict_type.value}."
        ]
        
        if supporting > 0:
            reasoning_parts.append(f"{supporting} sources support the claim.")
        if refuting > 0:
            reasoning_parts.append(f"{refuting} sources refute the claim.")
        
        # Add top source reference
        if evidence_list:
            top_source = evidence_list[0]
            reasoning_parts.append(
                f"Primary source: {top_source.source.domain} "
                f"(credibility: {top_source.source.credibility_score:.0f}, "
                f"stance: {top_source.stance.value})."
            )
        
        reasoning_parts.append(
            f"Consensus: {consensus_result['consensus_percentage']:.0f}% of sources agree."
        )
        
        return " ".join(reasoning_parts)

