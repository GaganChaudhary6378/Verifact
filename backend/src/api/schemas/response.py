"""API response schemas for VeriFact."""

from typing import List, Optional

from pydantic import BaseModel, Field

from ...config.constants import VerdictType, StanceType


class Citation(BaseModel):
    """Source citation with detailed metadata.
    
    Provides information about sources used to reach the verdict,
    including credibility, relevance, and stance.
    """

    source_name: str = Field(..., description="Display name of the source")
    url: str = Field(..., description="Full URL to the source")
    relevance_snippet: str = Field(..., description="Relevant text snippet from source")
    trust_score: float = Field(..., ge=0, le=1, description="Trust/credibility score (0-1)")
    stance: Optional[str] = Field(default=None, description="Stance towards claim (supports/refutes/neutral)")
    relevance_score: Optional[float] = Field(default=None, ge=0, le=1, description="Relevance to claim (0-1)")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "source_name": "Reuters",
                "url": "https://reuters.com/article/...",
                "relevance_snippet": "Scientists confirm with high confidence that...",
                "trust_score": 0.95,
                "stance": "supports",
                "relevance_score": 0.92,
            }
        }


class VerifyResponse(BaseModel):
    """Final verdict response (API contract).
    
    Contains the verification result with supporting evidence and citations.
    """

    request_id: str = Field(..., description="Unique request identifier")
    verdict: VerdictType = Field(..., description="Verdict: TRUE | FALSE | MISLEADING | NOT ENOUGH EVIDENCE")
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence (0-1)")
    reasoning_summary: str = Field(..., description="Human-readable explanation of the verdict")
    citations: List[Citation] = Field(..., description="Supporting source citations")
    quality_metrics: Optional[dict] = Field(default=None, description="Quality assessment metrics")
    consensus_info: Optional[dict] = Field(default=None, description="Consensus statistics")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "request_id": "req_a1b2c3d4",
                "verdict": "TRUE",
                "confidence_score": 0.92,
                "reasoning_summary": "Multiple credible sources confirm this claim with consistent evidence...",
                "citations": [
                    {
                        "source_name": "Reuters",
                        "url": "https://reuters.com/...",
                        "relevance_snippet": "Scientists confirm with 95% confidence that...",
                        "trust_score": 0.95,
                        "stance": "supports",
                        "relevance_score": 0.92,
                    }
                ],
                "quality_metrics": {
                    "faithfulness": 0.89,
                    "context_precision": 0.85,
                },
                "consensus_info": {
                    "supporting_sources": 5,
                    "refuting_sources": 0,
                    "neutral_sources": 2,
                    "consensus_percentage": 71.4,
                }
            }
        }


class AgentStepMessage(BaseModel):
    """Agent progress step message."""

    type: str = Field(default="AGENT_STEP", description="Message type")
    payload: dict = Field(..., description="Step details")


class FinalVerdictMessage(BaseModel):
    """Final verdict message."""

    type: str = Field(default="FINAL_VERDICT", description="Message type")
    payload: VerifyResponse = Field(..., description="Verdict response")

