"""Threshold evaluator for verdict classification."""

from loguru import logger

from ..config.constants import VerdictType
from ..config.settings import get_settings


class ThresholdEvaluator:
    """Evaluates consensus results against thresholds to determine verdict."""

    def __init__(self) -> None:
        """Initialize threshold evaluator."""
        self.settings = get_settings()
        logger.info("Threshold evaluator initialized")

    def evaluate(self, consensus_result: dict) -> VerdictType:
        """
        Evaluate consensus against thresholds.

        Args:
            consensus_result: Consensus calculation result

        Returns:
            Verdict type
        """
        weighted_score = consensus_result.get("weighted_score", 0.0)
        consensus_percentage = consensus_result.get("consensus_percentage", 0.0)
        total_sources = consensus_result.get("total_sources", 0)
        stance_distribution = consensus_result.get("stance_distribution", {})

        logger.info(
            f"Evaluating thresholds: score={weighted_score:.2f}, "
            f"consensus={consensus_percentage:.1f}%, sources={total_sources}"
        )

        # Check if insufficient evidence
        if total_sources < self.settings.min_sources_count:
            logger.info(f"Insufficient sources: {total_sources} < {self.settings.min_sources_count}")
            return VerdictType.NOT_ENOUGH_EVIDENCE

        # Calculate support vs refute weights
        supports_weight = stance_distribution.get("supports", 0.0)
        refutes_weight = stance_distribution.get("refutes", 0.0)
        neutral_weight = stance_distribution.get("neutral", 0.0)
        total_weight = supports_weight + refutes_weight + neutral_weight

        # If we have clear support or refutation (even with low consensus), use it
        if total_weight > 0:
            support_ratio = supports_weight / total_weight
            refute_ratio = refutes_weight / total_weight
            
            # Strong support: more than 50% of weight is supporting
            if support_ratio > 0.50 and weighted_score > 0:
                logger.info(f"Strong support: {support_ratio:.1%} of evidence supports")
                return VerdictType.TRUE
            
            # Strong refutation: more than 50% of weight is refuting
            if refute_ratio > 0.50 and weighted_score < 0:
                logger.info(f"Strong refutation: {refute_ratio:.1%} of evidence refutes")
                return VerdictType.FALSE
        
        # Check minimum confidence threshold
        if abs(weighted_score) < self.settings.min_confidence_threshold:
            logger.info(f"Low confidence: |{weighted_score}| < {self.settings.min_confidence_threshold}")
            return VerdictType.NOT_ENOUGH_EVIDENCE

        # Use original thresholds for very high confidence cases
        if (
            weighted_score >= self.settings.supported_score_threshold
            and consensus_percentage >= self.settings.min_consensus_percentage
        ):
            logger.info("Verdict: TRUE (high confidence)")
            return VerdictType.TRUE

        # Check for REFUTED
        if (
            weighted_score <= self.settings.refuted_score_threshold
            and consensus_percentage >= self.settings.min_consensus_percentage
        ):
            logger.info("Verdict: FALSE (REFUTED)")
            return VerdictType.FALSE

        # Mixed evidence or low consensus
        if consensus_percentage < self.settings.min_consensus_percentage:
            logger.info(f"Mixed evidence: consensus={consensus_percentage:.1f}%")
            return VerdictType.MISLEADING

        # Default to MISLEADING for ambiguous cases
        logger.info("Verdict: MISLEADING (default)")
        return VerdictType.MISLEADING

    def get_confidence_score(self, consensus_result: dict) -> float:
        """
        Calculate confidence score (0-1) for the verdict.

        Args:
            consensus_result: Consensus calculation result

        Returns:
            Confidence score
        """
        weighted_score = abs(consensus_result.get("weighted_score", 0.0))
        consensus_percentage = consensus_result.get("consensus_percentage", 0.0)
        total_sources = consensus_result.get("total_sources", 0)

        # Normalize weighted_score to 0-1 (assume max is 100)
        score_confidence = min(weighted_score / 100.0, 1.0)

        # Normalize consensus_percentage to 0-1
        consensus_confidence = consensus_percentage / 100.0

        # Factor in number of sources (more sources = more confidence)
        source_factor = min(total_sources / 5.0, 1.0)  # Cap at 5 sources

        # Weighted average: 40% score, 40% consensus, 20% source count
        confidence = (
            score_confidence * 0.4 +
            consensus_confidence * 0.4 +
            source_factor * 0.2
        )
        
        # Ensure minimum confidence of 0.4 if we have at least some evidence
        if total_sources > 0 and confidence < 0.4:
            confidence = 0.4

        return float(confidence)

