"""Constants and enums for VeriFact.

This module defines all enums, constants, and static configuration used across
the application. These values should not change at runtime.
"""

from enum import Enum


class VerdictType(str, Enum):
    """Verdict types for claim verification.
    
    - TRUE: Claim is supported by evidence
    - FALSE: Claim is refuted by evidence
    - MISLEADING: Claim is partially true but lacks context or is deceptive
    - NOT_ENOUGH_EVIDENCE: Insufficient evidence to make determination
    """

    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    NOT_ENOUGH_EVIDENCE = "NOT ENOUGH EVIDENCE"


class ClaimType(str, Enum):
    """Types of claims for classification.
    
    - FACTUAL: Objective facts that can be verified
    - STATISTICAL: Claims involving numbers, percentages, or statistics
    - EVENT: Claims about past or current events
    - PREDICTION: Claims about future events
    - OPINION: Subjective opinions or beliefs (generally not verifiable)
    """

    FACTUAL = "factual"
    STATISTICAL = "statistical"
    EVENT = "event"
    PREDICTION = "prediction"
    OPINION = "opinion"


class SourceCategory(str, Enum):
    """Categories of information sources with credibility implications.
    
    Ordered roughly by default credibility (highest to lowest):
    - ACADEMIC: Peer-reviewed journals, research institutions
    - GOVERNMENT: Government agencies and official sources
    - WIRE_SERVICE: News wire services (Reuters, AP)
    - FACT_CHECKER: Professional fact-checking organizations
    - MAINSTREAM: Established mainstream media outlets
    - WEB_SEARCH: General web search results
    - BLOG: Blog posts and opinion pieces
    - SOCIAL_MEDIA: Social media posts
    - CONSPIRACY: Known conspiracy or disinformation sources
    """

    WIRE_SERVICE = "wire_service"
    MAINSTREAM = "mainstream"
    FACT_CHECKER = "fact_checker"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    CONSPIRACY = "conspiracy"
    BLOG = "blog"
    SOCIAL_MEDIA = "social_media"
    WEB_SEARCH = "web_search"


class StanceType(str, Enum):
    """Stance of a source towards a claim.
    
    - SUPPORTS: Evidence confirms or validates the claim
    - REFUTES: Evidence contradicts or disproves the claim
    - NEUTRAL: Evidence neither supports nor refutes (informational)
    - UNRELATED: Evidence is not relevant to the claim
    """

    SUPPORTS = "supports"
    REFUTES = "refutes"
    NEUTRAL = "neutral"
    UNRELATED = "unrelated"


# ============================================================================
# SCORING THRESHOLDS (defaults - can be overridden in settings.py)
# ============================================================================

SUPPORTED_THRESHOLD = 75
"""Weighted score threshold for TRUE verdict (higher = stricter)"""

REFUTED_THRESHOLD = -50
"""Weighted score threshold for FALSE verdict (lower = stricter)"""

MIN_CONSENSUS = 70
"""Minimum consensus percentage required (0-100)"""

MIN_SOURCES = 3
"""Minimum number of sources required for confident verdict"""

MIN_CONFIDENCE = 60
"""Minimum confidence score required (0-100)"""


# ============================================================================
# REDIS CONFIGURATION
# ============================================================================

KNOWLEDGE_BASE_INDEX = "idx:knowledge_base"
"""Redis index name for knowledge base documents"""

VERIFIED_CLAIMS_INDEX = "idx:verified_claims"
"""Redis index name for cached verified claims"""

KB_DOC_PREFIX = "kb:doc:"
"""Redis key prefix for knowledge base documents"""

VERIFIED_CLAIM_PREFIX = "verified:claim:"
"""Redis key prefix for verified claims"""

CACHE_PREFIX = "cache:"
"""Redis key prefix for general cache entries"""


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

STANCE_MODEL = "microsoft/deberta-v3-base"
"""Model name for NLI-based stance detection (if used)"""


# ============================================================================
# SEARCH CONFIGURATION
# ============================================================================

MAX_WEB_RESULTS = 10
"""Maximum number of web search results to retrieve"""

MAX_NEWS_RESULTS = 10
"""Maximum number of news articles to retrieve"""

MAX_FACT_CHECK_RESULTS = 5
"""Maximum number of fact-check articles to retrieve"""


# ============================================================================
# TEXT PROCESSING
# ============================================================================

MAX_TEXT_LENGTH = 10000
"""Maximum text length for processing (characters)"""

MIN_CLAIM_LENGTH = 10
"""Minimum claim length (characters)"""

MAX_CLAIM_LENGTH = 1000
"""Maximum claim length (characters)"""


# ============================================================================
# TIMEOUTS AND LIMITS
# ============================================================================

API_TIMEOUT_SECONDS = 30
"""Default timeout for external API calls"""

MAX_RETRIES = 3
"""Maximum number of retries for failed API calls"""

RATE_LIMIT_DELAY = 1.0
"""Delay between rate-limited API calls (seconds)"""

