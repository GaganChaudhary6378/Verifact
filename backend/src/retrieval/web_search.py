"""Web search retriever using Exa Python SDK.

This module provides real-time web search capabilities for fact-checking
using the Exa API with semantic search and content extraction.
"""

from typing import List, Optional
from uuid import uuid4

from exa_py import Exa
from loguru import logger

from ..config.constants import MAX_WEB_RESULTS, SourceCategory, StanceType
from ..config.settings import get_settings
from ..models.claim import Claim
from ..models.evidence import Evidence, Source
from ..scoring.credibility import CredibilityScorer


class WebSearchRetriever:
    """Retrieves real-time evidence from web using Exa API.
    
    Provides semantic search across the web with content extraction
    and relevance scoring.
    """

    def __init__(self) -> None:
        """Initialize web search retriever with Exa client and credibility scorer."""
        self.settings = get_settings()
        self.credibility_scorer = CredibilityScorer()  # Add credibility scorer
        
        if not self.settings.exa_api_key:
            logger.warning("⚠️  Exa API key not configured - web search disabled")
            self.exa = None
        else:
            self.exa = Exa(api_key=self.settings.exa_api_key)
            logger.info("✓ Web search retriever initialized (Exa Python SDK)")

    def _extract_domain(self, url: str) -> str:
        """Extract clean domain from URL.
        
        Args:
            url: Full URL string
            
        Returns:
            Domain without www prefix
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain if domain else "unknown"
        except Exception as e:
            logger.debug(f"Failed to parse URL {url}: {e}")
            return "unknown"

    def retrieve(
        self,
        claim: Claim,
        top_k: int = MAX_WEB_RESULTS,
        geo_context: Optional[dict] = None,
    ) -> List[Evidence]:
        """Retrieve web evidence using Exa Search + Content API.

        Args:
            claim: Claim to search for
            top_k: Number of results to retrieve (max 10)
            geo_context: Optional geographic context for localized search

        Returns:
            List of Evidence objects from web sources
        """
        if not self.exa:
            logger.warning("Exa client not initialized - skipping web search")
            return []

        # Handle both Claim object and string
        claim_text = claim.normalized_text if hasattr(claim, 'normalized_text') else str(claim)
        logger.info(f"🔎 Retrieving web evidence for: {claim_text[:80]}...")

        try:
            # Step 1: Search with Exa
            logger.debug(f"Exa Search API: searching web (top_k={min(top_k, 10)})")
            
            search_result = self.exa.search(
                claim_text,
                num_results=min(top_k, 10),  # Exa API limit
                use_autoprompt=True,  # Use AI to improve query
            )

            if not search_result.results:
                logger.info("No web results found")
                return []

            logger.info(f"✓ Found {len(search_result.results)} web results")
            
            # Step 2: Get content for URLs
            urls = [r.url for r in search_result.results if r.url]
            
            if not urls:
                logger.info("No valid URLs found in search results")
                return []
            
            logger.debug(f"Exa Content API: fetching content for {len(urls)} URLs")
            
            content_result = self.exa.get_contents(
                urls,
                text={"max_characters": 2000},
                highlights={"num_sentences": 3, "highlights_per_url": 2}
            )
            
            logger.info(f"✓ Retrieved content for {len(content_result.results)} URLs")

            # Step 3: Create Evidence objects
            evidence_list = []
            for content_item in content_result.results:
                try:
                    evidence = self._content_to_evidence(content_item)
                    if evidence:
                        evidence_list.append(evidence)
                except Exception as e:
                    url = getattr(content_item, 'url', 'unknown')
                    logger.warning(f"Error processing web result from {url}: {e}")
                    continue

            logger.info(f"✓ Retrieved {len(evidence_list)} web evidence items")
            return evidence_list

        except Exception as e:
            logger.error(f"Exa API error during web search: {e}")
            # Graceful degradation - return empty list
            return []

    def _content_to_evidence(self, content_item) -> Optional[Evidence]:
        """Convert Exa content item to Evidence object.
        
        Args:
            content_item: Exa API content result
            
        Returns:
            Evidence object or None if conversion fails
        """
        try:
            url = content_item.url
            if not url:
                return None
            
            # Validate URL
            url_str = str(url)
            if not url_str.startswith('http'):
                logger.debug(f"Skipping invalid URL: {url_str}")
                return None

            domain = self._extract_domain(url_str)
            title = getattr(content_item, 'title', None) or "Web Article"
            
            # Get content (prefer text, fallback to highlights)
            text_content = getattr(content_item, 'text', None)
            highlights = getattr(content_item, 'highlights', None) or []
            
            if text_content:
                content = text_content[:2000]
            elif highlights:
                content = " ".join(highlights)
            else:
                logger.debug(f"Skipping {url_str} - no content available")
                return None

            # Validate content length
            if len(content) < 10:
                logger.debug(f"Skipping {url_str} - content too short")
                return None

            # Get Exa's highlight scores (their AI-computed relevance/quality)
            highlight_scores = getattr(content_item, 'highlight_scores', None) or []
            
            # Get domain credibility from our database
            cred_info = self.credibility_scorer.score_source(domain)
            domain_credibility = float(cred_info["score"])  # 0-100
            
            # Calculate trust score based on available data
            if highlight_scores:
                # We have Exa's quality assessment - use hybrid scoring
                exa_score = sum(highlight_scores) / len(highlight_scores)
                exa_score = min(1.0, max(0.0, exa_score))  # Clamp to 0-1
                
                # Combined trust: 50% domain reputation + 50% Exa content quality
                combined_trust = (domain_credibility * 0.5) + (exa_score * 100 * 0.5)
                relevance = exa_score
                
                logger.debug(
                    f"Source: {domain}, Domain: {domain_credibility:.0f}/100, "
                    f"Exa Quality: {exa_score*100:.0f}/100, Combined: {combined_trust:.0f}/100"
                )
            else:
                # No Exa scores available - use only domain credibility
                # This is honest: we only know the source's reputation
                combined_trust = domain_credibility
                relevance = 0.6  # Conservative relevance estimate
                
                logger.debug(
                    f"Source: {domain}, Trust: {combined_trust:.0f}/100 (domain only, no Exa score)"
                )

            # Create Source with combined trust score
            source = Source(
                source_id=f"web_{uuid4().hex[:8]}",
                url=url_str,
                domain=domain,
                title=title,
                snippet=content[:300],
                credibility_score=combined_trust,  # Combined score
                category=SourceCategory.WEB_SEARCH,
            )

            # Create Evidence
            evidence = Evidence(
                evidence_id=f"web_ev_{uuid4().hex[:8]}",
                source=source,
                content=content,
                relevance_score=relevance,  # Use Exa's relevance directly
                stance=StanceType.NEUTRAL,  # Determined by stance detector
                stance_confidence=0.0,
            )

            return evidence

        except Exception as e:
            logger.debug(f"Failed to convert content to evidence: {e}")
            return None

    def retrieve_sync(
        self,
        claim: Claim,
        top_k: int = MAX_WEB_RESULTS
    ) -> List[Evidence]:
        """Synchronous wrapper for retrieve (Exa SDK is already sync).
        
        Args:
            claim: Claim to search for
            top_k: Number of results
            
        Returns:
            List of Evidence objects
        """
        return self.retrieve(claim, top_k)
