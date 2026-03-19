"""Stance detection using OpenAI LLM."""

from typing import List, Tuple

from loguru import logger
from openai import OpenAI

from ..config.constants import StanceType
from ..config.settings import get_settings


class StanceDetector:
    """Detects stance of evidence towards claim using OpenAI LLM."""

    def __init__(self) -> None:
        """Initialize stance detector with OpenAI client."""
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model = "gpt-4o-mini"  # Fast and cost-effective for stance detection
        
        logger.info(f"Stance detector initialized with OpenAI {self.model}")

    def detect_stance(self, claim: str, evidence: str) -> Tuple[StanceType, float]:
        """
        Detect stance of evidence towards claim using LLM.

        Args:
            claim: Claim text
            evidence: Evidence text

        Returns:
            Tuple of (stance, confidence)
        """
        try:
            # Truncate evidence if too long to avoid token limits
            max_evidence_length = 1500
            if len(evidence) > max_evidence_length:
                evidence = evidence[:max_evidence_length] + "..."
                
            prompt = f"""You are a fact-checking assistant analyzing whether evidence supports, refutes, or is neutral towards a claim.

CLAIM: {claim}

EVIDENCE: {evidence}

INSTRUCTIONS:
1. Carefully compare the claim with the evidence
2. Determine the relationship:
   - SUPPORTS: Evidence confirms, validates, or agrees with the claim (even partially)
   - REFUTES: Evidence contradicts, disproves, or disagrees with the claim
   - NEUTRAL: Evidence is unrelated, ambiguous, or provides no clear position

3. Assign a confidence score (0.0-1.0):
   - 0.9-1.0: Strong, direct evidence
   - 0.7-0.89: Clear evidence with minor caveats
   - 0.5-0.69: Moderate, indirect evidence
   - 0.3-0.49: Weak or tangential evidence
   - 0.0-0.29: Very weak or unclear evidence

RESPOND WITH EXACTLY THIS FORMAT:
[SUPPORTS|REFUTES|NEUTRAL] [confidence]

Example: "SUPPORTS 0.85" or "REFUTES 0.92" or "NEUTRAL 0.60"
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise, analytical fact-checking assistant. Be objective and evidence-based."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,  # More deterministic
                max_tokens=50,
            )
            
            result = response.choices[0].message.content.strip().upper()
            logger.debug(f"Stance detection raw response: {result}")
            
            # Parse response more robustly
            parts = result.split()
            stance_str = ""
            confidence = 0.7  # Better default than 0.5
            
            # Try to extract stance and confidence
            for part in parts:
                if "SUPPORT" in part:
                    stance_str = "SUPPORTS"
                elif "REFUTE" in part:
                    stance_str = "REFUTES"
                elif "NEUTRAL" in part:
                    stance_str = "NEUTRAL"
                else:
                    # Try to parse as float
                    try:
                        parsed_conf = float(part)
                        if 0.0 <= parsed_conf <= 1.0:
                            confidence = parsed_conf
                    except (ValueError, IndexError):
                        continue
            
            # If no stance detected, default to NEUTRAL
            if not stance_str:
                stance_str = "NEUTRAL"
                confidence = 0.6
            
            # Map to StanceType
            if stance_str == "SUPPORTS":
                return StanceType.SUPPORTS, confidence
            elif stance_str == "REFUTES":
                return StanceType.REFUTES, confidence
            else:
                return StanceType.NEUTRAL, confidence
                
        except Exception as e:
            logger.error(f"Stance detection error: {e}")
            return StanceType.NEUTRAL, 0.6  # Slightly higher default

    def detect_batch(
        self,
        claim: str,
        evidence_list: List[str],
        batch_size: int = 8,
    ) -> List[Tuple[StanceType, float]]:
        """
        Detect stance for multiple evidence items.

        Args:
            claim: Claim text
            evidence_list: List of evidence texts
            batch_size: Not used (kept for compatibility)

        Returns:
            List of (stance, confidence) tuples
        """
        results = []
        
        for evidence in evidence_list:
            stance, confidence = self.detect_stance(claim, evidence)
            results.append((stance, confidence))
        
        return results

