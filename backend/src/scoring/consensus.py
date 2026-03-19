"""Consensus calculation using credibility-weighted voting."""

from typing import Dict, List

from loguru import logger

from ..config.constants import StanceType
from ..models.evidence import Evidence


class ConsensusCalculator:
    """Calculates weighted consensus from multiple evidence sources."""

    def __init__(self) -> None:
        """Initialize consensus calculator."""
        logger.info("Consensus calculator initialized")

    def calculate(self, evidence_list: List[Evidence]) -> dict:
        """
        Calculate credibility-weighted consensus.

        Args:
            evidence_list: List of evidence with credibility scores and stances

        Returns:
            Dict with consensus results
        """
        if not evidence_list:
            return {
                "weighted_score": 0.0,
                "consensus_percentage": 0.0,
                "total_sources": 0,
                "stance_distribution": {},
                "credibility_total": 0.0,
            }

        # Initialize counters
        stance_weights: Dict[StanceType, float] = {
            StanceType.SUPPORTS: 0.0,
            StanceType.REFUTES: 0.0,
            StanceType.NEUTRAL: 0.0,
            StanceType.UNRELATED: 0.0,
        }

        total_credibility = 0.0

        # Aggregate weighted stances
        for evidence in evidence_list:
            try:
                credibility = evidence.source.credibility_score
                stance = evidence.stance
                stance_confidence = evidence.stance_confidence
                
                # Validate values
                if credibility <= 0:
                    logger.warning(f"Invalid credibility score: {credibility}, defaulting to 0.5")
                    credibility = 0.5
                    
                if not 0.0 <= stance_confidence <= 1.0:
                    logger.warning(f"Invalid stance confidence: {stance_confidence}, defaulting to 0.7")
                    stance_confidence = 0.7

                # Weight by both credibility and stance confidence
                weight = credibility * stance_confidence

                stance_weights[stance] += weight
                total_credibility += credibility
                
            except Exception as e:
                logger.error(f"Error processing evidence stance: {e}")
                # Skip this evidence item
                continue

        # Calculate weighted score (-100 to +100)
        if total_credibility == 0 or total_credibility < 0.01:
            logger.warning(f"Total credibility too low or zero: {total_credibility}")
            weighted_score = 0.0
        else:
            # Supports: positive, Refutes: negative, Neutral: 0
            score_sum = (
                stance_weights[StanceType.SUPPORTS]
                - stance_weights[StanceType.REFUTES]
            )
            # Normalize to -100 to +100
            weighted_score = (score_sum / total_credibility) * 100

        # Calculate consensus percentage (agreement level)
        if total_credibility == 0 or total_credibility < 0.01:
            consensus_percentage = 0.0
        else:
            # Percentage of weight in the dominant stance
            max_weight = max(stance_weights.values())
            consensus_percentage = (max_weight / total_credibility) * 100
            
            # Ensure consensus is meaningful - if all neutral, lower the consensus
            if stance_weights[StanceType.NEUTRAL] == max_weight:
                consensus_percentage *= 0.8  # Reduce consensus for neutral-heavy evidence

        # Stance distribution
        stance_distribution = {
            stance.value: weight
            for stance, weight in stance_weights.items()
        }

        result = {
            "weighted_score": weighted_score,
            "consensus_percentage": consensus_percentage,
            "total_sources": len(evidence_list),
            "stance_distribution": stance_distribution,
            "credibility_total": total_credibility,
        }

        logger.info(
            f"Consensus: score={weighted_score:.2f}, "
            f"consensus={consensus_percentage:.1f}%, "
            f"sources={len(evidence_list)}"
        )
        
        # Log stance distribution for debugging
        logger.debug(f"Stance distribution: {stance_distribution}")

        return result

    def get_dominant_stance(self, stance_distribution: Dict[str, float]) -> StanceType:
        """
        Get dominant stance from distribution.

        Args:
            stance_distribution: Stance weight distribution

        Returns:
            Dominant stance
        """
        if not stance_distribution:
            return StanceType.NEUTRAL

        max_stance = max(stance_distribution.items(), key=lambda x: x[1])
        return StanceType(max_stance[0])

