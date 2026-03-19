"""Application settings using Pydantic Settings.

This module provides centralized configuration management for the VeriFact application.
All settings can be overridden using environment variables or .env file.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger


class Settings(BaseSettings):
    """Application configuration with validation and type safety.
    
    Environment variables override default values. Use .env file for local development.
    All sensitive values (API keys) should be set via environment variables in production.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================================================
    # API KEYS - Must be set via environment variables
    # ============================================================================
    
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for LLM and embeddings",
    )
    
    exa_api_key: str = Field(
        default="",
        description="Exa API key for web search and fact-checking",
    )
    
    news_api_key: str = Field(
        default="",
        description="NewsAPI key for news retrieval (optional)",
    )
    
    cohere_api_key: str = Field(
        default="",
        description="Cohere API key for reranking (optional)",
    )

    # ============================================================================
    # REDIS CONFIGURATION - Vector database and caching
    # ============================================================================
    
    redis_host: str = Field(
        default="localhost",
        description="Redis server hostname",
    )
    redis_port: int = Field(
        default=6379,
        ge=1,
        le=65535,
        description="Redis server port",
    )
    redis_db: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Redis database number (0-15)",
    )
    redis_password: str = Field(
        default="",
        description="Redis password (if authentication enabled)",
    )

    # ============================================================================
    # LLM & EMBEDDING CONFIGURATION
    # ============================================================================
    
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model",
    )
    embedding_dim: int = Field(
        default=1536,
        description="Embedding dimensions (1536 for text-embedding-3-small)",
    )
    
    primary_llm: str = Field(
        default="gpt-4o-mini",
        description="Primary LLM model for reasoning tasks",
    )
    llm_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0=deterministic, 2=creative)",
    )
    llm_max_tokens: int = Field(
        default=4096,
        ge=100,
        le=16000,
        description="Maximum tokens for LLM responses",
    )

    # ============================================================================
    # RETRIEVAL CONFIGURATION
    # ============================================================================
    
    top_k_retrieval: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Number of documents to retrieve initially",
    )
    rerank_top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of documents after reranking",
    )
    chunk_size: int = Field(
        default=512,
        ge=128,
        le=2048,
        description="Text chunk size for indexing",
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=256,
        description="Overlap between chunks",
    )

    # ============================================================================
    # SCORING & VERDICT THRESHOLDS
    # ============================================================================
    
    supported_score_threshold: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Weighted score threshold for TRUE verdict",
    )
    refuted_score_threshold: int = Field(
        default=-50,
        ge=-100,
        le=0,
        description="Weighted score threshold for FALSE verdict",
    )
    min_consensus_percentage: int = Field(
        default=55,
        ge=0,
        le=100,
        description="Minimum consensus percentage required",
    )
    min_sources_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Minimum number of sources required",
    )
    min_confidence_threshold: int = Field(
        default=40,
        ge=0,
        le=100,
        description="Minimum confidence threshold for verdicts",
    )

    # ============================================================================
    # RAGAS QUALITY GATES - Evaluation metrics
    # ============================================================================
    
    min_faithfulness: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description="Minimum faithfulness score (groundedness in evidence)",
    )
    min_context_precision: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="Minimum context precision score",
    )
    min_answer_correctness: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Minimum answer correctness score",
    )
    cache_min_faithfulness: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum faithfulness score for caching",
    )

    # ============================================================================
    # CACHING CONFIGURATION
    # ============================================================================
    
    cache_ttl_seconds: int = Field(
        default=86400,
        ge=3600,
        le=604800,
        description="Cache TTL in seconds (default: 24 hours)",
    )
    cache_similarity_threshold: float = Field(
        default=0.95,
        ge=0.8,
        le=1.0,
        description="Similarity threshold for cache hits (cosine similarity)",
    )

    # ============================================================================
    # API SERVER CONFIGURATION
    # ============================================================================
    
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host (0.0.0.0 for all interfaces)",
    )
    api_port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="API server port",
    )
    api_reload: bool = Field(
        default=True,
        description="Enable auto-reload in development",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    
    # CORS Configuration
    allowed_origins: str = Field(
        default="http://localhost:3000,chrome-extension://*",
        description="Comma-separated list of allowed CORS origins",
    )
    
    # Request limits
    max_claim_length: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Maximum claim text length in characters",
    )
    request_timeout_seconds: int = Field(
        default=120,
        ge=30,
        le=300,
        description="Maximum request processing time in seconds",
    )

    # ============================================================================
    # VALIDATORS
    # ============================================================================
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v
    
    # ============================================================================
    # COMPUTED PROPERTIES
    # ============================================================================
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins string into list.
        
        Returns:
            List of origin strings
        """
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL.
        
        Returns:
            Redis URL string
        """
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode.
        
        Returns:
            True if production environment
        """
        return not self.api_reload
    
    def validate_api_keys(self) -> dict:
        """Validate that required API keys are configured.
        
        Returns:
            Dict with validation status for each service
        """
        status = {
            "openai": bool(self.openai_api_key),
            "exa": bool(self.exa_api_key),
            "cohere": bool(self.cohere_api_key),
            "news_api": bool(self.news_api_key),
        }
        return status


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.
    
    This function is cached to ensure singleton behavior across the application.
    The settings are loaded once and reused for all requests.
    
    Returns:
        Settings instance
        
    Raises:
        ValidationError: If configuration is invalid
    """
    try:
        settings = Settings()
        
        # Validate critical API keys
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured - LLM features will not work")
        if not settings.exa_api_key:
            logger.warning("Exa API key not configured - web search will be disabled")
            
        return settings
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

