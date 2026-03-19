"""Index knowledge base documents to Redis Stack."""

import json
import time
from pathlib import Path
from typing import List
from uuid import uuid4

from loguru import logger

from ..config.settings import get_settings
from ..core.embeddings import EmbeddingManager
from ..core.redis_client import RedisClient


def load_sample_documents() -> List[dict]:
    """
    Load sample documents for indexing.

    Returns:
        List of document dicts
    """
    # Sample knowledge base documents
    documents = [
        {
            "content": "The Earth is an oblate spheroid, meaning it is mostly spherical but slightly flattened at the poles and bulging at the equator. This shape has been confirmed through satellite imagery, physics, and direct observation from space.",
            "source": "wikipedia.org",
            "category": "science",
            "url": "https://en.wikipedia.org/wiki/Earth",
        },
        {
            "content": "Climate change refers to long-term shifts in temperatures and weather patterns. Since the 1800s, human activities have been the main driver of climate change, primarily due to burning fossil fuels like coal, oil and gas.",
            "source": "un.org",
            "category": "science",
            "url": "https://www.un.org/en/climatechange/what-is-climate-change",
        },
        {
            "content": "Vaccines work by training the immune system to recognize and combat pathogens. The claim that vaccines cause autism has been thoroughly debunked by numerous scientific studies and medical organizations worldwide.",
            "source": "cdc.gov",
            "category": "health",
            "url": "https://www.cdc.gov/vaccinesafety/",
        },
        {
            "content": "The COVID-19 pandemic was first identified in December 2019 in Wuhan, China. The World Health Organization declared it a Public Health Emergency of International Concern in January 2020 and a pandemic in March 2020.",
            "source": "who.int",
            "category": "health",
            "url": "https://www.who.int/health-topics/coronavirus",
        },
        {
            "content": "5G is the fifth generation of cellular network technology. There is no scientific evidence that 5G networks cause COVID-19 or any other health problems. Radio waves from mobile networks are non-ionizing and do not damage DNA.",
            "source": "who.int",
            "category": "technology",
            "url": "https://www.who.int/news-room/questions-and-answers/item/radiation-5g-mobile-networks-and-health",
        },
        {
            "content": "Artificial Intelligence (AI) is intelligence demonstrated by machines, in contrast to natural intelligence displayed by humans. Modern AI includes machine learning, deep learning, and large language models.",
            "source": "wikipedia.org",
            "category": "technology",
            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        },
        {
            "content": "The Apollo 11 mission landed humans on the Moon on July 20, 1969. Neil Armstrong and Buzz Aldrin became the first humans to walk on the lunar surface. This achievement has been verified through physical evidence, independent tracking, and samples brought back to Earth.",
            "source": "nasa.gov",
            "category": "history",
            "url": "https://www.nasa.gov/mission_pages/apollo/apollo-11.html",
        },
        {
            "content": "Evolution by natural selection is the scientific theory explaining how species change over time. It is supported by evidence from paleontology, genetics, comparative anatomy, and molecular biology.",
            "source": "nature.com",
            "category": "science",
            "url": "https://www.nature.com/subjects/evolution",
        },
    ]

    return documents


def index_documents(
    redis_client: RedisClient,
    embedding_manager: EmbeddingManager,
    documents: List[dict],
) -> None:
    """
    Index documents to Redis Stack.

    Args:
        redis_client: Redis client instance
        embedding_manager: Embedding manager instance
        documents: List of documents to index
    """
    logger.info(f"Indexing {len(documents)} documents...")

    for doc in documents:
        try:
            # Generate embedding
            content = doc["content"]
            embedding = embedding_manager.embed_text(content)

            # Prepare document data
            doc_id = uuid4().hex
            doc_data = {
                "content": content,
                "content_vector": embedding,
                "source": doc["source"],
                "category": doc["category"],
                "url": doc["url"],
                "timestamp": int(time.time()),
            }

            # Add to Redis
            redis_client.add_document(doc_id, doc_data)

            logger.info(f"Indexed document: {doc['source']} - {content[:50]}...")

        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            continue

    logger.info(f"✓ Indexed {len(documents)} documents successfully")


def main() -> None:
    """Main indexing function."""
    logger.info("Starting knowledge base indexing...")

    # Initialize components
    redis_client = RedisClient()
    embedding_manager = EmbeddingManager()

    # Ensure indexes exist
    redis_client.create_knowledge_base_index()

    # Load and index documents
    documents = load_sample_documents()
    index_documents(redis_client, embedding_manager, documents)

    # Close connection
    redis_client.close()

    logger.info("✓ Knowledge base indexing complete!")


if __name__ == "__main__":
    main()

