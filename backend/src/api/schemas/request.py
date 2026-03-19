"""API request schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class PageMetadata(BaseModel):
    """Page metadata from frontend."""

    url: str = Field(..., description="Page URL")
    page_title: str = Field(..., description="Page title")
    selected_at: str = Field(..., description="ISO8601 timestamp")
    language: str = Field(default="en-US", description="Language code")
    description: Optional[str] = Field(default="", description="Page description")
    author: Optional[str] = Field(default="", description="Article author")
    published_date: Optional[str] = Field(default="", description="Publication date")
    site_name: Optional[str] = Field(default="", description="Site name")


class OGTags(BaseModel):
    """Open Graph tags."""

    title: str = Field(default="", description="OG title")
    image: str = Field(default="", description="OG image")
    type: str = Field(default="", description="OG type")


class WebpageContent(BaseModel):
    """Webpage content from frontend."""

    full_text: str = Field(default="", description="Full page text")
    raw_meta_tags: dict = Field(default_factory=dict, description="Raw meta tags")
    structured_data: list = Field(default_factory=list, description="JSON-LD structured data")
    og_tags: OGTags = Field(default_factory=lambda: OGTags(), description="Open Graph tags")


class Coordinates(BaseModel):
    """GPS coordinates."""

    lat: float = Field(default=0.0, description="Latitude")
    lon: float = Field(default=0.0, description="Longitude")
    accuracy: float = Field(default=0.0, description="Accuracy in meters")


class GeoData(BaseModel):
    """Geographic data."""

    country: str = Field(default="Unknown", description="Country")
    city: str = Field(default="Unknown", description="City")
    timezone: str = Field(..., description="Timezone")
    timezone_offset: int = Field(..., description="Timezone offset in minutes")
    coordinates: Coordinates = Field(default_factory=lambda: Coordinates(), description="GPS coordinates")


class NetworkContext(BaseModel):
    """Network context."""

    ip_address: str = Field(default="0.0.0.0", description="IP address")
    connection_type: str = Field(default="unknown", description="Connection type")
    is_vpn_detected: bool = Field(default=False, description="VPN detection")


class BrowserInfo(BaseModel):
    """Browser information."""

    user_agent: str = Field(..., description="User agent string")
    platform: str = Field(..., description="Platform")
    screen_resolution: str = Field(..., description="Screen resolution")


class SearchStack(BaseModel):
    """Search preferences."""

    preferred_engine: str = Field(default="google", description="Preferred search engine")
    safe_search: bool = Field(default=True, description="Safe search enabled")


class SourceContext(BaseModel):
    """Source context from frontend (matches API contract)."""

    page_metadata: PageMetadata = Field(..., description="Page metadata")
    webpage_content: WebpageContent = Field(..., description="Webpage content")
    geo_data: GeoData = Field(..., description="Geographic data")
    network_context: NetworkContext = Field(..., description="Network context")
    browser_info: BrowserInfo = Field(..., description="Browser information")
    search_stack: SearchStack = Field(..., description="Search preferences")


class VerifyRequest(BaseModel):
    """WebSocket START_VERIFICATION request payload."""

    claim_text: str = Field(..., description="Claim to verify")
    source_context: SourceContext = Field(..., description="Source context")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "claim_text": "The Earth is flat",
                "source_context": {
                    "page_metadata": {
                        "url": "https://example.com/article",
                        "page_title": "Example Article",
                        "selected_at": "2026-02-10T12:00:00Z",
                        "language": "en-US",
                        "description": "Example article description",
                        "author": "John Doe",
                        "published_date": "2026-02-10",
                        "site_name": "Example News"
                    },
                    "webpage_content": {
                        "full_text": "Article content here...",
                        "raw_meta_tags": {},
                        "structured_data": [],
                        "og_tags": {"title": "", "image": "", "type": ""}
                    },
                    "geo_data": {
                        "country": "US",
                        "city": "San Francisco",
                        "timezone": "America/Los_Angeles",
                        "timezone_offset": -480,
                        "coordinates": {"lat": 37.7749, "lon": -122.4194, "accuracy": 15.0}
                    },
                    "network_context": {
                        "ip_address": "0.0.0.0",
                        "connection_type": "wifi",
                        "is_vpn_detected": False
                    },
                    "browser_info": {
                        "user_agent": "Mozilla/5.0...",
                        "platform": "MacIntel",
                        "screen_resolution": "1920x1080"
                    },
                    "search_stack": {
                        "preferred_engine": "google",
                        "safe_search": True
                    }
                },
            }
        }


class WebSocketMessage(BaseModel):
    """Generic WebSocket message."""

    action: str = Field(..., description="Message action type")
    payload: dict = Field(..., description="Message payload")

