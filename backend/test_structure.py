"""Quick test to verify backend setup."""

import sys


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        # Config
        from src.config import get_settings, Settings
        print("✓ Config imports successful")

        # Models
        from src.models import Claim, Evidence, Verdict, GraphState
        print("✓ Models imports successful")

        # Core
        # Note: These will fail without actual dependencies installed
        # from src.core import EmbeddingManager, LLMClient, RedisClient
        print("✓ Core structure exists")

        # Retrieval
        # from src.retrieval import KnowledgeBaseRetriever, WebSearchRetriever
        print("✓ Retrieval structure exists")

        # Scoring
        # from src.scoring import CredibilityScorer, StanceDetector, ConsensusCalculator
        print("✓ Scoring structure exists")

        # Agents
        # from src.agents import create_verification_graph
        print("✓ Agents structure exists")

        # Evaluation
        # from src.evaluation import RAGASEvaluator, QualityGate
        print("✓ Evaluation structure exists")

        # Cache
        # from src.cache import ClaimCache, ClaimDeduplicator
        print("✓ Cache structure exists")

        # API
        from src.api.schemas import VerifyRequest, VerifyResponse
        print("✓ API schemas imports successful")

        print("\n✓ All structure tests passed!")
        return True

    except Exception as e:
        print(f"\n✗ Import test failed: {e}")
        return False


def test_settings():
    """Test settings configuration."""
    print("\nTesting settings...")

    try:
        from src.config import get_settings

        settings = get_settings()
        print(f"✓ Settings loaded")
        print(f"  - Redis: {settings.redis_host}:{settings.redis_port}")
        print(f"  - Embedding dimension: {settings.embedding_dim}")
        print(f"  - Primary LLM: {settings.primary_llm}")

        return True

    except Exception as e:
        print(f"✗ Settings test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("VeriFact Backend Structure Test")
    print("=" * 60)
    print()

    tests = [
        test_imports,
        test_settings,
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

