from pydantic import BaseModel
from typing import Optional


class VetResponse(BaseModel):
    """Response model for the /vet endpoint."""
    success: bool
    media_type: str
    analysis: Optional[str] = None
    error: Optional[str] = None

