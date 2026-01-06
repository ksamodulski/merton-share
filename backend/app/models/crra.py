"""Pydantic models for CRRA survey."""

from typing import Dict
from pydantic import BaseModel, Field


class CRRASurveyRequest(BaseModel):
    """Request model for CRRA calculation from survey."""

    loss_threshold: float = Field(
        ...,
        ge=0,
        le=100,
        description="Max tolerable loss percentage (0-100)",
    )
    risk_percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Max loss accepted in 50/50 gamble for 50% gain (0-100)",
    )
    stock_allocation: float = Field(
        ...,
        ge=0,
        le=100,
        description="Preferred allocation to risky assets (0-100)",
    )
    safe_choice: float = Field(
        ...,
        ge=0,
        le=100,
        description="Job security probability required for variable income (0-100)",
    )


class RiskProfile(BaseModel):
    """Risk profile interpretation."""

    risk_profile: str
    description: str
    typical_allocation: str
    investor_type: str
    percentile: str


class CRRAResponse(BaseModel):
    """Response model for CRRA calculation."""

    crra: float = Field(..., ge=1, le=10, description="Calculated CRRA value")
    profile: RiskProfile


class CRRAInterpretRequest(BaseModel):
    """Request to interpret a CRRA value."""

    crra: float = Field(..., ge=1, le=10, description="CRRA value to interpret")


class CRRAScaleItem(BaseModel):
    """Single item in CRRA scale description."""

    range: str
    profile: str
    typical_investor: str


class CRRAScaleResponse(BaseModel):
    """Response with full CRRA scale description."""

    scale: list[CRRAScaleItem]
