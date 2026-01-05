from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


TIER_FILE_LIMITS = {
    Tier.FREE: 5 * 1024 * 1024,
    Tier.PRO: 25 * 1024 * 1024,
    Tier.ENTERPRISE: 150 * 1024 * 1024
}


class VetResponse(BaseModel):
    success: bool
    media_type: str
    tier: str
    analysis: Optional[str] = None
    error: Optional[str] = None

