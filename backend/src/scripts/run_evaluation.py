"""Run RAGAS evaluation on test claims."""

import json
from pathlib import Path

from loguru import logger

from ..config.settings import get_settings
from ..core.embeddings import EmbeddingManager
from ..core.llm import LLMClient
from ..core.redis_client import RedisClient
from ..agents.graph import create_verification_graph
from ..evaluation.ragas_metrics import RAGASEvaluator


def load_test_claims() -> list:
    """
    Load test claims from data file.

    Returns:
        List of test claim dicts
    """
    data_path = Path(__file__).parent.parent / "data" / "test_claims.json"

    try:
        with open(data_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Test claims file not found, using default")
        return [
            {
                "claim": "The Earth is flat",
                "ground_truth": "FALSE",
                "category": "science",
            }
        ]


def main() -> None:
    """Run evaluation on test claims."""
    logger.info("Starting RAGAS evaluation...")

    # Initialize components
    redis_client = RedisClient()
    embedding_manager = EmbeddingManager()
    llm_client = LLMClient()

    # Create verification graph
    graph = create_verification_graph(redis_client, embedding_manager, llm_client)

    # Initialize evaluator
    evaluator = RAGASEvaluator()

    # Load test claims
    test_claims = load_test_claims()
    logger.info(f"Loaded {len(test_claims)} test claims")

    # Evaluate each claim
    results = []

    for i, test_claim in enumerate(test_claims, 1):
        logger.info(f"\n[{i}/{len(test_claims)}] Evaluating: {test_claim['claim']}")

        try:
            # Run verification
            state = {
                "request_id": f"eval_{i}",
                "raw_claim": test_claim["claim"],
                "source_context": None,
                "kb_evidence": [],
                "web_evidence": [],
                "fact_check_evidence": [],
                "all_evidence": [],
                "quality_passed": True,
                "current_step": "",
                "progress_messages": [],
            }

            result_state = graph.invoke(state)
            verdict = result_state.get("verdict")

            if not verdict:
                logger.error("No verdict produced")
                continue

            # Evaluate with RAGAS
            ragas_scores = evaluator.evaluate_verdict(
                test_claim["claim"],
                result_state.get("all_evidence", []),
                verdict,
                ground_truth=test_claim.get("ground_truth"),
            )

            # Collect results
            results.append({
                "claim": test_claim["claim"],
                "predicted_verdict": verdict.verdict_type.value,
                "ground_truth": test_claim.get("ground_truth"),
                "confidence": verdict.confidence_score,
                "faithfulness": ragas_scores.get("faithfulness"),
                "context_precision": ragas_scores.get("context_precision"),
                "answer_correctness": ragas_scores.get("answer_correctness"),
            })

            logger.info(f"Verdict: {verdict.verdict_type.value} (confidence: {verdict.confidence_score:.2f})")
            logger.info(f"RAGAS scores: {ragas_scores}")

        except Exception as e:
            logger.error(f"Error evaluating claim: {e}")
            continue

    # Calculate average metrics
    if results:
        avg_faithfulness = sum(r["faithfulness"] or 0 for r in results) / len(results)
        avg_precision = sum(r["context_precision"] or 0 for r in results) / len(results)
        avg_correctness = sum(r["answer_correctness"] or 0 for r in results if r["answer_correctness"]) / len([r for r in results if r["answer_correctness"]])

        logger.info("\n" + "=" * 60)
        logger.info("EVALUATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total claims evaluated: {len(results)}")
        logger.info(f"Average Faithfulness: {avg_faithfulness:.3f}")
        logger.info(f"Average Context Precision: {avg_precision:.3f}")
        logger.info(f"Average Answer Correctness: {avg_correctness:.3f}")
        logger.info("=" * 60)

        # Save results
        output_path = Path(__file__).parent.parent.parent / "evaluation_results.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to: {output_path}")

    redis_client.close()
    logger.info("✓ Evaluation complete!")


if __name__ == "__main__":
    main()

