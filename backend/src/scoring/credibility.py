"""Source credibility scoring."""

import json
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from ..config.constants import SourceCategory


class CredibilityScorer:
    """Assigns credibility scores to sources based on domain database."""

    def __init__(self, credibility_db_path: Optional[str] = None) -> None:
        """
        Initialize credibility scorer.

        Args:
            credibility_db_path: Path to credibility database JSON
        """
        if credibility_db_path is None:
            # Default path
            base_path = Path(__file__).parent.parent / "data" / "source_credibility.json"
            credibility_db_path = str(base_path)

        self.credibility_db: Dict[str, dict] = {}

        # Load credibility database
        try:
            with open(credibility_db_path, "r") as f:
                self.credibility_db = json.load(f)
            logger.info(f"Loaded {len(self.credibility_db)} sources from credibility database")
        except FileNotFoundError:
            logger.warning(f"Credibility database not found at {credibility_db_path}")
            # Use default database
            self.credibility_db = self._get_default_db()

    def _get_default_db(self) -> Dict[str, dict]:
        """Get default credibility database with comprehensive source ratings."""
        return {
            # Wire Services (Highest Credibility)
            "reuters.com": {"score": 95, "category": "wire_service", "bias": "center"},
            "apnews.com": {"score": 95, "category": "wire_service", "bias": "center"},
            "afp.com": {"score": 94, "category": "wire_service", "bias": "center"},
            
            # Mainstream News
            "bbc.com": {"score": 90, "category": "mainstream", "bias": "center-left"},
            "bbc.co.uk": {"score": 90, "category": "mainstream", "bias": "center-left"},
            "cnn.com": {"score": 75, "category": "mainstream", "bias": "left"},
            "foxnews.com": {"score": 70, "category": "mainstream", "bias": "right"},
            "nytimes.com": {"score": 85, "category": "mainstream", "bias": "center-left"},
            "washingtonpost.com": {"score": 85, "category": "mainstream", "bias": "center-left"},
            "wsj.com": {"score": 88, "category": "mainstream", "bias": "center-right"},
            "theguardian.com": {"score": 82, "category": "mainstream", "bias": "left"},
            "npr.org": {"score": 87, "category": "mainstream", "bias": "center-left"},
            "pbs.org": {"score": 88, "category": "mainstream", "bias": "center"},
            
            # Fact Checkers
            "snopes.com": {"score": 92, "category": "fact_checker", "bias": "center"},
            "politifact.com": {"score": 90, "category": "fact_checker", "bias": "center"},
            "factcheck.org": {"score": 88, "category": "fact_checker", "bias": "center"},
            "fullfact.org": {"score": 87, "category": "fact_checker", "bias": "center"},
            
            # Academic & Research
            "nature.com": {"score": 98, "category": "academic", "bias": "center"},
            "science.org": {"score": 98, "category": "academic", "bias": "center"},
            "sciencedirect.com": {"score": 96, "category": "academic", "bias": "center"},
            "springer.com": {"score": 96, "category": "academic", "bias": "center"},
            "wiley.com": {"score": 95, "category": "academic", "bias": "center"},
            "arxiv.org": {"score": 92, "category": "academic", "bias": "center"},
            "pubmed.ncbi.nlm.nih.gov": {"score": 97, "category": "academic", "bias": "center"},
            
            # Government & Official Sources
            "nih.gov": {"score": 97, "category": "government", "bias": "center"},
            "cdc.gov": {"score": 95, "category": "government", "bias": "center"},
            "who.int": {"score": 92, "category": "government", "bias": "center"},
            "fda.gov": {"score": 95, "category": "government", "bias": "center"},
            "nasa.gov": {"score": 96, "category": "government", "bias": "center"},
            
            # Tech Documentation & Blogs (Developer Resources)
            "docs.openai.com": {"score": 88, "category": "mainstream", "bias": "center"},
            "stackoverflow.com": {"score": 82, "category": "mainstream", "bias": "center"},
            "github.com": {"score": 80, "category": "mainstream", "bias": "center"},
            "medium.com": {"score": 65, "category": "blog", "bias": "center"},
            "towardsdatascience.com": {"score": 72, "category": "blog", "bias": "center"},
            "dev.to": {"score": 68, "category": "blog", "bias": "center"},
            "geeksforgeeks.org": {"score": 70, "category": "blog", "bias": "center"},
            "datacamp.com": {"score": 75, "category": "blog", "bias": "center"},
            "realpython.com": {"score": 78, "category": "blog", "bias": "center"},
            "chromadb.dev": {"score": 85, "category": "mainstream", "bias": "center"},
            "streamlinehq.com": {"score": 65, "category": "blog", "bias": "center"},
            "thelinuxcode.com": {"score": 68, "category": "blog", "bias": "center"},
            "linkedin.com": {"score": 60, "category": "social_media", "bias": "center"},
            "celerdata.com": {"score": 70, "category": "mainstream", "bias": "center"},
            "gopenai.com": {"score": 65, "category": "blog", "bias": "center"},
            "pingcap.com": {"score": 72, "category": "mainstream", "bias": "center"},
            "cloudflare.com": {"score": 82, "category": "mainstream", "bias": "center"},
            "algolia.com": {"score": 78, "category": "mainstream", "bias": "center"},
            
            # Low Credibility / Conspiracy
            "infowars.com": {"score": 15, "category": "conspiracy", "bias": "far-right"},
            "breitbart.com": {"score": 40, "category": "blog", "bias": "far-right"},
            "naturalnews.com": {"score": 20, "category": "conspiracy", "bias": "far-right"},
        }

    def get_domain_from_url(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain string
        """
        # Remove protocol
        domain = url.replace("https://", "").replace("http://", "")
        # Remove path
        domain = domain.split("/")[0]
        # Remove www
        domain = domain.replace("www.", "")
        return domain.lower()

    def score_source(self, domain: str) -> dict:
        """
        Get credibility score for a domain.

        Args:
            domain: Domain name

        Returns:
            Dict with score, category, and bias
        """
        domain = domain.lower().replace("www.", "")

        if domain in self.credibility_db:
            return self.credibility_db[domain]

        # Check for subdomain match
        for db_domain, data in self.credibility_db.items():
            if domain.endswith(db_domain):
                return data

        # Default for unknown sources (slightly more generous for web content)
        return {
            "score": 60,  # Slightly above neutral for general web content
            "category": "blog",
            "bias": "unknown",
        }

    def score_url(self, url: str) -> dict:
        """
        Get credibility score for a URL.

        Args:
            url: Full URL

        Returns:
            Dict with score, category, and bias
        """
        domain = self.get_domain_from_url(url)
        return self.score_source(domain)

    def update_source_credibility(self, domain: str, score: float, category: str, bias: str) -> None:
        """
        Update or add source to credibility database.

        Args:
            domain: Domain name
            score: Credibility score (0-100)
            category: Source category
            bias: Political bias
        """
        self.credibility_db[domain.lower()] = {
            "score": score,
            "category": category,
            "bias": bias,
        }

