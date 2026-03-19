"""Configuration module for VeriFact."""

from .settings import get_settings, Settings
from .constants import (
    VerdictType,
    ClaimType,
    SourceCategory,
    SUPPORTED_THRESHOLD,
    REFUTED_THRESHOLD,
    MIN_CONSENSUS,
    MIN_SOURCES,
)

__all__ = [
    "get_settings",
    "Settings",
    "VerdictType",
    "ClaimType",
    "SourceCategory",
    "SUPPORTED_THRESHOLD",
    "REFUTED_THRESHOLD",
    "MIN_CONSENSUS",
    "MIN_SOURCES",
]

