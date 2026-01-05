from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Tier(str, Enum):
    """Subscription tiers with their file size limits."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# File size limits in bytes per tier
TIER_FILE_LIMITS = {
    Tier.FREE: 5 * 1024 * 1024,        # 5 MB
    Tier.PRO: 25 * 1024 * 1024,        # 25 MB
    Tier.ENTERPRISE: 150 * 1024 * 1024  # 150 MB
}


class VetResponse(BaseModel):
    """Response model for the /vet endpoint."""
    success: bool
    media_type: str
    tier: str
    analysis: Optional[str] = None
    error: Optional[str] = None

