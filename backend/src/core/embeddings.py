"""Embedding manager using OpenAI embeddings API."""

from typing import List

from loguru import logger
from openai import OpenAI

from ..config.settings import get_settings


class EmbeddingManager:
    """Manages embedding generation using OpenAI embeddings API."""

    def __init__(self) -> None:
        """Initialize embedding manager."""
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model = "text-embedding-3-small"  # 1536 dimensions, cheaper and faster than ada-002
        self.dimension = 1536

        logger.info(f"Embedding manager initialized with OpenAI {self.model}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using OpenAI API.

        Args:
            text: Input text

        Returns:
            Embedding vector as list of floats
        """
        try:
            # Replace newlines for better embedding quality
            text = text.replace("\n", " ")
            
            response = self.client.embeddings.create(
                input=text,
                model=self.model,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self.dimension

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using OpenAI API.

        Args:
            texts: List of input texts
            batch_size: Batch size for encoding (OpenAI supports up to 2048)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            # Clean texts
            cleaned_texts = [text.replace("\n", " ") for text in texts]
            
            # Process in batches
            all_embeddings = []
            for i in range(0, len(cleaned_texts), batch_size):
                batch = cleaned_texts[i:i + batch_size]
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.model,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                if len(texts) > 100:
                    logger.info(f"Embedded {len(all_embeddings)}/{len(texts)} texts")
            
            return all_embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            # Return zero vectors as fallback
            return [[0.0] * self.dimension for _ in texts]

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        embeddings = self.embed_batch([text1, text2])
        emb1 = embeddings[0]
        emb2 = embeddings[1]

        # Cosine similarity using list operations (no numpy needed)
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a * a for a in emb1) ** 0.5
        norm2 = sum(b * b for b in emb2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def compute_similarity_matrix(self, texts: List[str]) -> List[List[float]]:
        """
        Compute pairwise similarity matrix for texts.

        Args:
            texts: List of texts

        Returns:
            NxN similarity matrix as list of lists
        """
        embeddings = self.embed_batch(texts)
        n = len(embeddings)
        
        # Compute similarity matrix without numpy
        similarity_matrix = []
        for i in range(n):
            row = []
            for j in range(n):
                dot_product = sum(a * b for a, b in zip(embeddings[i], embeddings[j]))
                norm_i = sum(a * a for a in embeddings[i]) ** 0.5
                norm_j = sum(b * b for b in embeddings[j]) ** 0.5
                
                if norm_i == 0 or norm_j == 0:
                    similarity = 0.0
                else:
                    similarity = dot_product / (norm_i * norm_j)
                
                row.append(similarity)
            similarity_matrix.append(row)
        
        return similarity_matrix

