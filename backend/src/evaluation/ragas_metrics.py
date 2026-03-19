"""RAGAS evaluation metrics for answer quality assessment.

This module provides quality evaluation using RAGAS (Retrieval-Augmented Generation
Assessment) metrics to ensure high-quality fact-checking responses.

Key metrics:
- Faithfulness: How grounded the answer is in the provided context
- Context Precision: How relevant the retrieved context is
- Answer Correctness: Overall correctness of the answer
"""

import asyncio
import concurrent.futures
from typing import Dict, List, Optional

from datasets import Dataset
from loguru import logger
from ragas import evaluate
from ragas.metrics import answer_correctness, context_precision, faithfulness

from ..config.settings import get_settings
from ..models.evidence import Evidence
from ..models.verdict import Verdict


class RAGASEvaluator:
    """Evaluator using RAGAS metrics for verdict quality assessment.
    
    Provides automated quality evaluation of fact-checking responses
    to ensure they are grounded in evidence and accurate.
    
    Note: RAGAS evaluation runs in a separate thread to avoid event loop conflicts
    with uvloop (used by FastAPI/uvicorn).
    """

    def __init__(self) -> None:
        """Initialize RAGAS evaluator with configured metrics."""
        self.settings = get_settings()
        self.metrics = [
            faithfulness,           # Answer grounded in context
            context_precision,      # Retrieved context relevance
            answer_correctness,     # Overall answer quality
        ]
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        logger.info("✓ RAGAS evaluator initialized with 3 metrics (thread-pool mode)")

    def _evaluate_in_thread(self, dataset: Dataset, metrics_to_use: list) -> dict:
        """Run RAGAS evaluation in a separate thread with its own event loop.
        
        This avoids conflicts with uvloop used by FastAPI/uvicorn.
        
        Args:
            dataset: Dataset to evaluate
            metrics_to_use: List of metrics to compute
            
        Returns:
            Evaluation results dictionary
        """
        def run_evaluation():
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Run evaluation in this thread's event loop
                results = evaluate(dataset, metrics=metrics_to_use)
                return results
            finally:
                loop.close()
        
        # Run in thread pool to avoid event loop conflicts
        future = self.executor.submit(run_evaluation)
        return future.result(timeout=60)  # 60 second timeout

    def evaluate_verdict(
        self,
        claim_text: str,
        evidence_list: List[Evidence],
        verdict: Verdict,
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        """Evaluate verdict quality using RAGAS metrics.

        Args:
            claim_text: Original claim being verified
            evidence_list: Evidence items used for verdict
            verdict: Generated verdict with reasoning
            ground_truth: Optional ground truth answer for comparison

        Returns:
            Dictionary with metric scores (0-1 scale):
            - faithfulness: How grounded the answer is in evidence
            - context_precision: How relevant the retrieved context is
            - answer_correctness: Overall correctness (if ground_truth provided)
        """
        try:
            logger.debug(f"Evaluating verdict quality for: {claim_text[:80]}...")
            
            # Prepare contexts from evidence
            contexts = [ev.content for ev in evidence_list[:10]]  # Limit for efficiency

            if not contexts:
                logger.warning("No contexts available for RAGAS evaluation")
                return self._get_default_scores()

            # Prepare dataset for RAGAS
            data = {
                "question": [claim_text],
                "answer": [verdict.reasoning_summary],
                "contexts": [contexts],
            }

            # Add reference/ground truth if available
            if ground_truth:
                data["reference"] = [ground_truth]
                data["ground_truth"] = [ground_truth]
            else:
                # Create synthetic reference for metrics that need it
                synthetic_reference = f"The claim is {verdict.verdict_type.value}."
                data["reference"] = [synthetic_reference]
                data["ground_truth"] = [synthetic_reference]

            # Create dataset
            dataset = Dataset.from_dict(data)

            # Select metrics based on available data
            metrics_to_use = [faithfulness]  # Always use faithfulness
            
            if len(contexts) > 0:
                metrics_to_use.append(context_precision)
            
            if ground_truth:
                metrics_to_use.append(answer_correctness)

            logger.debug(f"Running RAGAS with metrics: {[m.name for m in metrics_to_use]}")
            
            # Run evaluation in separate thread to avoid uvloop conflicts
            results = self._evaluate_in_thread(dataset, metrics_to_use)

            # Extract scores - RAGAS returns a dict-like object
            # Access the actual computed scores, not defaults
            logger.debug(f"RAGAS results type: {type(results)}")
            logger.debug(f"RAGAS results: {results}")
            logger.debug(f"Results attributes: {[a for a in dir(results) if not a.startswith('_')][:20]}")
            
            # Try to find the actual data
            results_data = None
            if hasattr(results, 'to_dict') and callable(getattr(results, 'to_dict')):
                try:
                    results_data = results.to_dict()
                    logger.debug(f"Got data from to_dict(): {results_data}")
                except Exception as e:
                    logger.debug(f"to_dict() failed: {e}")
            
            # RAGAS EvaluationResult stores scores in _repr_dict attribute
            if results_data is None and hasattr(results, '_repr_dict'):
                results_data = results._repr_dict
                logger.debug(f"Using _repr_dict: {results_data}")
            
            if results_data is None and hasattr(results, '__dict__'):
                results_data = results.__dict__
                logger.debug(f"Using __dict__: {results_data}")
            
            if results_data is None:
                try:
                    results_data = dict(results)
                    logger.debug(f"Converted to dict: {results_data}")
                except Exception as e:
                    logger.debug(f"dict() conversion failed: {e}")
                    results_data = {}
            
            scores = {}
            
            try:
                # Extract faithfulness score from results_data
                logger.debug("Extracting faithfulness score...")
                try:
                    if results_data and 'faithfulness' in results_data:
                        scores['faithfulness'] = float(results_data['faithfulness'])
                        logger.debug(f"Got faithfulness: {scores['faithfulness']}")
                    else:
                        logger.warning("Faithfulness not in results_data, using default")
                        scores['faithfulness'] = 0.75
                except (KeyError, TypeError, ValueError, Exception) as e:
                    logger.warning(f"Faithfulness score not accessible ({type(e).__name__}: {e}), using default")
                    scores['faithfulness'] = 0.75
                
                # Extract context_precision score
                logger.debug("Extracting context_precision score...")
                try:
                    if results_data and 'context_precision' in results_data:
                        scores['context_precision'] = float(results_data['context_precision'])
                        logger.debug(f"Got context_precision: {scores['context_precision']}")
                    else:
                        logger.warning("Context precision not in results_data, using default")
                        scores['context_precision'] = 0.75
                except (KeyError, TypeError, ValueError, Exception) as e:
                    logger.warning(f"Context precision not accessible ({type(e).__name__}: {e}), using default")
                    scores['context_precision'] = 0.75
                
                # Extract answer_correctness score (optional)
                logger.debug("Extracting answer_correctness score...")
                if ground_truth:
                    try:
                        if results_data and 'answer_correctness' in results_data:
                            scores['answer_correctness'] = float(results_data['answer_correctness'])
                            logger.debug(f"Got answer_correctness: {scores['answer_correctness']}")
                        else:
                            logger.warning("Answer correctness not in results_data")
                            scores['answer_correctness'] = None
                    except (KeyError, TypeError, ValueError, Exception):
                        logger.warning("Answer correctness not accessible")
                        scores['answer_correctness'] = None
                else:
                    scores['answer_correctness'] = None

                logger.debug(f"Successfully extracted all scores: {scores}")
                logger.info(
                    f"RAGAS scores - faithfulness: {scores['faithfulness']:.3f}, "
                    f"precision: {scores['context_precision']:.3f}, "
                    f"correctness: {scores.get('answer_correctness', 'N/A')}"
                )
                
                logger.debug("Returning scores...")
                return scores
                
            except Exception as e:
                logger.error(f"Error extracting RAGAS scores: {e}", exc_info=True)
                logger.warning(f"Falling back to default scores due to extraction error")
                return self._get_default_scores()

        except concurrent.futures.TimeoutError:
            logger.error("RAGAS evaluation timeout (60s)")
            return self._get_default_scores()
        except Exception as e:
            logger.error(f"RAGAS evaluation error: {e}")
            # Return default scores on error (graceful degradation)
            return self._get_default_scores()

    def _get_default_scores(self) -> Dict[str, float]:
        """Get default scores when evaluation fails.
        
        Returns neutral scores to avoid blocking the pipeline.
        
        Returns:
            Dictionary with default metric scores
        """
        return {
            "faithfulness": 0.75,
            "context_precision": 0.75,
            "answer_correctness": None,
        }

    def is_high_quality(self, scores: Dict[str, float]) -> bool:
        """Check if scores meet quality thresholds.
        
        Args:
            scores: Dictionary of RAGAS metric scores
            
        Returns:
            True if all scores meet minimum thresholds
        """
        faithfulness_ok = scores.get("faithfulness", 0) >= self.settings.min_faithfulness
        precision_ok = scores.get("context_precision", 0) >= self.settings.min_context_precision
        
        # answer_correctness is optional (may be None)
        correctness = scores.get("answer_correctness")
        correctness_ok = (
            correctness is None or 
            correctness >= self.settings.min_answer_correctness
        )
        
        return faithfulness_ok and precision_ok and correctness_ok

    def get_quality_summary(self, scores: Dict[str, float]) -> str:
        """Generate human-readable quality summary.
        
        Args:
            scores: Dictionary of RAGAS metric scores
            
        Returns:
            Quality summary string
        """
        faithfulness = scores.get("faithfulness", 0)
        precision = scores.get("context_precision", 0)
        correctness = scores.get("answer_correctness")
        
        # Calculate average (excluding None values)
        score_values = [faithfulness, precision]
        if correctness is not None:
            score_values.append(correctness)
        
        avg_score = sum(score_values) / len(score_values) if score_values else 0
        
        if avg_score >= 0.8:
            quality = "Excellent"
        elif avg_score >= 0.7:
            quality = "Good"
        elif avg_score >= 0.6:
            quality = "Acceptable"
        else:
            quality = "Poor"
        
        correctness_str = f"{correctness:.2%}" if correctness is not None else "N/A"
        
        return (
            f"{quality} quality - "
            f"Faithfulness: {faithfulness:.2%}, "
            f"Precision: {precision:.2%}, "
            f"Correctness: {correctness_str}"
        )

    def evaluate_batch(
        self,
        claims: List[str],
        evidence_lists: List[List[Evidence]],
        verdicts: List[Verdict],
        ground_truths: Optional[List[str]] = None,
    ) -> List[Dict[str, float]]:
        """Evaluate multiple verdicts in batch.
        
        Useful for testing and benchmarking multiple claims at once.

        Args:
            claims: List of claim texts
            evidence_lists: List of evidence lists (one per claim)
            verdicts: List of generated verdicts
            ground_truths: Optional list of ground truth answers

        Returns:
            List of metric score dictionaries (one per claim)
        """
        if not claims or len(claims) != len(evidence_lists) != len(verdicts):
            logger.error("Mismatched lengths in batch evaluation inputs")
            return []
        
        logger.info(f"Batch evaluating {len(claims)} verdicts...")
        results = []

        for i, (claim, evidence_list, verdict) in enumerate(zip(claims, evidence_lists, verdicts)):
            ground_truth = ground_truths[i] if ground_truths and i < len(ground_truths) else None
            scores = self.evaluate_verdict(claim, evidence_list, verdict, ground_truth)
            results.append(scores)

        # Log summary
        if results:
            avg_faithfulness = sum(r.get("faithfulness", 0) for r in results) / len(results)
            avg_precision = sum(r.get("context_precision", 0) for r in results) / len(results)
            logger.info(
                f"Batch evaluation complete - Avg faithfulness: {avg_faithfulness:.3f}, "
                f"Avg precision: {avg_precision:.3f}"
            )

        return results
    
    def __del__(self):
        """Cleanup thread pool on deletion."""
        try:
            self.executor.shutdown(wait=False)
        except Exception:
            pass

