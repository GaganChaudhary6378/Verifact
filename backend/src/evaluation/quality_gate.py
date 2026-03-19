"""Quality gate logic for verdict validation."""

from loguru import logger

from ..config.constants import VerdictType
from ..config.settings import get_settings
from ..models.verdict import Verdict


class QualityGate:
    """Validates verdict quality against RAGAS thresholds."""

    def __init__(self) -> None:
        """Initialize quality gate."""
        self.settings = get_settings()
        logger.info("Quality gate initialized")

    def check(self, verdict: Verdict, ragas_scores: dict) -> bool:
        """
        Check if verdict passes quality gates.

        Args:
            verdict: Verdict to check
            ragas_scores: RAGAS evaluation scores

        Returns:
            True if passes, False otherwise
        """
        logger.info("Checking quality gates...")

        faithfulness = ragas_scores.get("faithfulness", 0.0)
        context_precision = ragas_scores.get("context_precision", 0.0)
        answer_correctness = ragas_scores.get("answer_correctness")

        passed = True
        reasons = []

        # Check faithfulness
        if faithfulness < self.settings.min_faithfulness:
            passed = False
            reasons.append(
                f"Faithfulness too low: {faithfulness:.2f} < {self.settings.min_faithfulness}"
            )

        # Check context precision
        if context_precision < self.settings.min_context_precision:
            passed = False
            reasons.append(
                f"Context precision too low: {context_precision:.2f} < {self.settings.min_context_precision}"
            )

        # Check answer correctness if available
        if answer_correctness is not None and answer_correctness < self.settings.min_answer_correctness:
            passed = False
            reasons.append(
                f"Answer correctness too low: {answer_correctness:.2f} < {self.settings.min_answer_correctness}"
            )

        if passed:
            logger.info("✓ Quality gates passed")
        else:
            logger.warning(f"✗ Quality gates failed: {'; '.join(reasons)}")

        return passed

    def should_cache(self, verdict: Verdict, ragas_scores: dict) -> bool:
        """
        Check if verdict should be cached.

        Args:
            verdict: Verdict to check
            ragas_scores: RAGAS scores

        Returns:
            True if should cache
        """
        faithfulness = ragas_scores.get("faithfulness", 0.0)

        # Only cache high-quality verdicts
        should_cache = faithfulness >= self.settings.cache_min_faithfulness

        if should_cache:
            logger.info(f"✓ Verdict eligible for caching (faithfulness={faithfulness:.2f})")
        else:
            logger.info(f"✗ Verdict not cached (faithfulness={faithfulness:.2f} < {self.settings.cache_min_faithfulness})")

        return should_cache

    def override_verdict(self, verdict: Verdict, passed: bool) -> Verdict:
        """
        Override verdict if quality gates fail.

        Args:
            verdict: Original verdict
            passed: Whether quality gates passed

        Returns:
            Modified verdict if needed
        """
        if not passed:
            logger.warning("Overriding verdict to NOT_ENOUGH_EVIDENCE due to quality gate failure")

            verdict.verdict_type = VerdictType.NOT_ENOUGH_EVIDENCE
            verdict.confidence_score = 0.3
            verdict.reasoning_summary = (
                "The verification process did not meet quality standards. "
                "More reliable evidence is needed to make a definitive determination. "
                f"Original assessment: {verdict.reasoning_summary}"
            )

        return verdict

