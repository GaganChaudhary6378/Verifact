"""Fact-checker retrieval using Exa Search + Content API.

This module retrieves evidence from professional fact-checking organizations
using semantic search and content extraction.
"""

import re
from typing import List, Optional
from uuid import uuid4

from exa_py import Exa
from loguru import logger

from ..config.constants import SourceCategory, StanceType
from ..config.settings import get_settings
from ..models.claim import Claim
from ..models.evidence import Evidence, Source
from ..scoring.credibility import CredibilityScorer


# Professional fact-checking websites (high credibility)
FACT_CHECK_DOMAINS = [
    "snopes.com",
    "factcheck.org",
    "politifact.com",
    "fullfact.org",
    "apnews.com/ap-fact-check",
]


class FactCheckerRetriever:
    """Retrieves evidence from professional fact-checking websites.
    
    Uses Exa API to search across trusted fact-checking organizations
    with high credibility scores.
    """

    def __init__(self) -> None:
        """Initialize fact-checker retriever with Exa client and credibility scorer."""
        self.settings = get_settings()
        self.credibility_scorer = CredibilityScorer()  # Add credibility scorer
        
        if not self.settings.exa_api_key:
            logger.warning("⚠️  Exa API key not configured - fact-checker retrieval disabled")
            self.exa = None
        else:
            self.exa = Exa(api_key=self.settings.exa_api_key)
            logger.info("✓ Fact-checker retriever initialized (Exa Search + Content API)")

    def _get_base_credibility(self, domain: str) -> float:
        """Get base credibility score for a fact-checking domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Credibility score (85-95 for known fact-checkers)
        """
        # Known fact-checker credibility scores
        domain_scores = {
            "snopes.com": 95.0,
            "factcheck.org": 92.0,
            "politifact.com": 90.0,
            "fullfact.org": 88.0,
            "apnews.com": 93.0,
        }
        
        domain_lower = domain.lower()
        for known_domain, score in domain_scores.items():
            if known_domain in domain_lower:
                return score
        
        # Default for unknown fact-checkers
        return 85.0

    def _extract_domain(self, url: str) -> str:
        """Extract clean domain from URL.
        
        Args:
            url: Full URL
            
        Returns:
            Domain without www prefix
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except Exception as e:
            logger.debug(f"Failed to parse URL {url}: {e}")
            return "unknown"
    
    def _clean_query(self, claim_text: str) -> str:
        """Clean and optimize claim text for fact-checker search.
        
        Removes pronunciation guides, special characters, and limits length
        for better search results.
        
        Args:
            claim_text: Raw claim text
            
        Returns:
            Cleaned query string optimized for search
        """
        # Remove bracketed content (pronunciation guides, etc.)
        query = re.sub(r'\[.*?\]', '', claim_text)
        
        # Remove IPA and special characters
        query = re.sub(r'[ˈˌːɦʊɡŋ]+', '', query)
        
        # Normalize whitespace
        query = ' '.join(query.split())
        
        # Keep meaningful words (skip very short words except important ones)
        words = query.split()
        meaningful_words = [
            w for w in words 
            if len(w) > 2 or w.lower() in {'is', 'in', 'of', 'to', 'at', 'on'}
        ]
        
        # Limit to 15 words for focused search
        query_short = " ".join(meaningful_words[:15])
        
        return query_short.strip()

    def retrieve(self, claim: Claim, top_k: int = 5) -> List[Evidence]:
        """Retrieve fact-check evidence using Exa Search + Content API.
        
        Flow:
        1. Clean and optimize claim text for search
        2. Use Exa Search API to find fact-check articles
        3. Extract unique URLs from results
        4. Use Exa Content API to get article content
        5. Combine data and create Evidence objects
        
        Args:
            claim: Claim to verify
            top_k: Max results to return (default 5)

        Returns:
            List of Evidence objects from fact-checkers, sorted by relevance
        """
        if not self.exa:
            logger.warning("Exa client not initialized - skipping fact-checker retrieval")
            return []

        # Handle both Claim object and string
        claim_text = claim.normalized_text if hasattr(claim, 'normalized_text') else str(claim)
        
        # Clean query for better search results
        query = self._clean_query(claim_text)
        
        logger.info(f"🔍 Retrieving fact-check evidence for: {query[:80]}...")
        logger.debug(f"Searching fact-checker domains: {', '.join(FACT_CHECK_DOMAINS)}")

        try:
            # Step 1: Search fact-checker sites with Exa
            logger.debug(f"Exa Search API: querying fact-checkers (top_k={top_k * 2})")
            
            search_result = self.exa.search(
                query,
                num_results=top_k * 2,  # Get more, filter later
                include_domains=FACT_CHECK_DOMAINS,
                use_autoprompt=True,
            )
            
            if not search_result.results:
                logger.info("No fact-check articles found")
                return []
            
            logger.info(f"✓ Found {len(search_result.results)} fact-check articles")
            
            # Step 2: Extract unique URLs and store search metadata
            search_data = {}
            unique_urls = []
            
            for result in search_result.results[:top_k * 2]:
                url = result.url
                if url and url not in unique_urls:
                    unique_urls.append(url)
                    
                    # Calculate average highlight score for relevance
                    highlight_scores = getattr(result, 'highlight_scores', None) or []
                    avg_highlight_score = (
                        sum(highlight_scores) / len(highlight_scores) 
                        if highlight_scores else 0.5
                    )
                    
                    search_data[url] = {
                        "title": result.title or "Fact Check Article",
                        "highlights": getattr(result, 'highlights', None) or [],
                        "highlight_score": avg_highlight_score,
                        "published_date": getattr(result, 'published_date', None),
                        "author": getattr(result, 'author', None),
                    }
            
            # Limit to top_k URLs
            unique_urls = unique_urls[:top_k]
            logger.debug(f"Extracted {len(unique_urls)} unique fact-checker URLs")
            
            # Step 3: Get content using Exa Content API
            logger.debug(f"Exa Content API: fetching content for {len(unique_urls)} URLs")
            
            content_result = self.exa.get_contents(
                unique_urls,
                text={"max_characters": 2000},
                highlights={"num_sentences": 5, "highlights_per_url": 3}
            )
            
            logger.info(f"✓ Retrieved content for {len(content_result.results)} URLs")
            
            # Step 4: Create Evidence objects
            evidence_list = []
            
            for content_item in content_result.results:
                try:
                    evidence = self._content_to_evidence(content_item, search_data)
                    if evidence:
                        evidence_list.append(evidence)
                except Exception as e:
                    url = getattr(content_item, 'url', 'unknown')
                    logger.warning(f"Error creating evidence for {url}: {e}")
                    continue
            
            logger.info(f"✓ Retrieved {len(evidence_list)} fact-check evidence items")
            return evidence_list
            
        except Exception as e:
            logger.error(f"Exa API error during fact-checker retrieval: {e}")
            # Graceful degradation
            return []

    def _content_to_evidence(self, content_item, search_data: dict) -> Optional[Evidence]:
        """Convert Exa content item to Evidence object.
        
        Args:
            content_item: Exa API content result
            search_data: Dictionary of search metadata by URL
            
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
            
            search_info = search_data.get(url_str, {})
            
            # Get title
            title = getattr(content_item, 'title', None) or search_info.get("title", "Fact Check Article")
            
            # Combine highlights from search and content
            search_highlights = search_info.get("highlights", [])
            content_highlights = getattr(content_item, 'highlights', None) or []
            all_highlights = search_highlights + content_highlights
            
            # Get content (prefer summary, then highlights, then text)
            summary = getattr(content_item, 'summary', None)
            text_content = getattr(content_item, 'text', None)
            
            if summary:
                content = summary
            elif all_highlights:
                content = " ".join(all_highlights)
            elif text_content:
                content = text_content[:2000]
            else:
                logger.debug(f"Skipping {url_str} - no content available")
                return None
            
            # Validate content length
            if len(content) < 10:
                logger.debug(f"Skipping {url_str} - content too short")
                return None
            
            # Calculate trust score using both domain reputation and Exa quality
            domain = self._extract_domain(url_str)
            cred_info = self.credibility_scorer.score_source(domain)
            domain_credibility = float(cred_info["score"])  # 0-100
            
            # Get Exa's highlight score (their AI assessment of content quality)
            exa_highlight_score = search_info.get("highlight_score", None)
            
            # Calculate trust based on available data
            if exa_highlight_score is not None and exa_highlight_score > 0:
                # We have Exa's quality assessment - use hybrid scoring
                # Combined trust: 60% domain reputation + 40% Exa content quality
                # Fact-checkers get more weight on domain since they're pre-vetted
                combined_trust = (domain_credibility * 0.6) + (exa_highlight_score * 100 * 0.4)
                relevance = min(0.95, 0.6 + exa_highlight_score * 0.4)
                
                logger.debug(
                    f"Fact-checker: {domain}, Domain: {domain_credibility:.0f}/100, "
                    f"Exa Quality: {exa_highlight_score*100:.0f}/100, Combined: {combined_trust:.0f}/100"
                )
            else:
                # No Exa score - use domain credibility only (honest approach)
                combined_trust = domain_credibility
                relevance = 0.8  # Fact-checkers typically have high relevance
                
                logger.debug(
                    f"Fact-checker: {domain}, Trust: {combined_trust:.0f}/100 (domain only, no Exa score)"
                )
            
            # Create Source with combined trust score
            source = Source(
                source_id=f"fc_{uuid4().hex[:8]}",
                url=url_str,
                domain=domain,
                title=title,
                snippet=content[:300],
                credibility_score=combined_trust,  # Combined domain + Exa quality
                category=SourceCategory.FACT_CHECKER,
            )
            
            # Create Evidence
            evidence = Evidence(
                evidence_id=f"fc_ev_{uuid4().hex[:8]}",
                source=source,
                content=content[:2000],  # Limit content length
                relevance_score=relevance,
                stance=StanceType.NEUTRAL,  # Will be determined by stance detector
                stance_confidence=0.0,
            )
            
            logger.debug(f"✓ Created evidence from {domain}: {title[:50]}...")
            return evidence
            
        except Exception as e:
            url_str = getattr(content_item, 'url', 'unknown')
            logger.debug(f"Failed to convert content to evidence for {url_str}: {e}")
            return None

    def retrieve_sync(self, claim: Claim, top_k: int = 5) -> List[Evidence]:
        """Synchronous wrapper for retrieve (Exa SDK is already sync).
        
        Args:
            claim: Claim to verify
            top_k: Max results
            
        Returns:
            List of Evidence objects
        """
        return self.retrieve(claim, top_k)
