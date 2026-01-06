"""Pydantic models for portfolio optimization."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import numpy as np


class OptimizationRequest(BaseModel):
    """Request model for Merton optimization."""

    assets: List[str] = Field(..., min_length=2, description="Asset identifiers")
    expected_returns: List[float] = Field(..., description="Expected returns (as decimals)")
    volatilities: List[float] = Field(..., description="Volatilities (as decimals)")
    correlation_matrix: List[List[float]] = Field(..., description="Correlation matrix")
    crra: float = Field(..., gt=0, le=10, description="CRRA parameter")

    @model_validator(mode="after")
    def validate_dimensions(self) -> "OptimizationRequest":
        """Validate all array dimensions match."""
        n = len(self.assets)

        if len(self.expected_returns) != n:
            raise ValueError(f"Expected {n} returns, got {len(self.expected_returns)}")
        if len(self.volatilities) != n:
            raise ValueError(f"Expected {n} volatilities, got {len(self.volatilities)}")
        if len(self.correlation_matrix) != n:
            raise ValueError(f"Expected {n}x{n} correlation matrix")
        for i, row in enumerate(self.correlation_matrix):
            if len(row) != n:
                raise ValueError(f"Correlation matrix row {i} has {len(row)} elements, expected {n}")

        # Validate volatilities are positive
        if any(v <= 0 for v in self.volatilities):
            raise ValueError("All volatilities must be positive")

        return self


class PortfolioStats(BaseModel):
    """Portfolio statistics."""

    return_pct: float = Field(..., alias="return", description="Expected return (%)")
    volatility: float = Field(..., description="Portfolio volatility (%)")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    crra_utility: float = Field(..., description="CRRA utility value")
    risk_contribution: Dict[str, float] = Field(..., description="Risk contribution by asset (%)")

    class Config:
        populate_by_name = True


class OptimizationResponse(BaseModel):
    """Response model for Merton optimization."""

    optimal_weights: Dict[str, float] = Field(..., description="Optimal weights by asset (%)")
    portfolio_stats: PortfolioStats


class GapAnalysisRow(BaseModel):
    """Single row in gap analysis."""

    ticker: str
    region: Optional[str] = None
    current_pct: float = Field(..., description="Current allocation (%)")
    target_pct: float = Field(..., description="Target allocation (%)")
    gap: float = Field(..., description="Gap (target - current)")
    priority: str = Field(
        ...,
        pattern="^(high|medium|consider|hold|skip)$",
        description="Priority level",
    )
    valuation_signal: Optional[str] = Field(
        None,
        pattern="^(favorable|neutral|cautious)$",
    )
    institutional_stance: Optional[str] = Field(
        None,
        pattern="^(overweight|neutral|underweight)$",
    )


class GapAnalysisRequest(BaseModel):
    """Request for gap analysis."""

    current_allocation: Dict[str, float] = Field(
        ..., description="Current allocation by asset (%)"
    )
    target_allocation: Dict[str, float] = Field(
        ..., description="Target allocation by asset (%)"
    )
    valuations: Optional[Dict[str, str]] = Field(
        None, description="Valuation signals by region"
    )
    institutional_stances: Optional[Dict[str, str]] = Field(
        None, description="Institutional stances by region"
    )


class GapAnalysisResponse(BaseModel):
    """Response with gap analysis."""

    rows: List[GapAnalysisRow]
    high_priority: List[str] = Field(..., description="Assets with high priority")
    medium_priority: List[str] = Field(..., description="Assets with medium priority")


class AllocationRecommendation(BaseModel):
    """Single allocation recommendation."""

    ticker: str
    isin: Optional[str] = None
    amount_eur: float = Field(..., ge=0)
    percentage_of_contribution: float = Field(..., ge=0, le=100)
    rationale: str


class AllocationRequest(BaseModel):
    """Request for allocation recommendation."""

    contribution_amount: float = Field(..., gt=0, description="Amount to allocate (EUR)")
    current_portfolio_value: float = Field(..., gt=0, description="Current portfolio value (EUR)")
    gap_analysis: GapAnalysisResponse
    min_allocation: float = Field(500.0, description="Minimum allocation per ETF (EUR)")


class AllocationResponse(BaseModel):
    """Response with allocation recommendations."""

    total_contribution: float
    recommendations: List[AllocationRecommendation]
    unallocated: float = Field(0.0, description="Amount not allocated")


class RebalanceCheckRequest(BaseModel):
    """Request for rebalancing check."""

    current_allocation: Dict[str, float] = Field(..., description="Current allocation by asset (%)")
    target_allocation: Dict[str, float] = Field(..., description="Target allocation by asset (%)")
    rebalance_threshold: float = Field(5.0, ge=1.0, le=20.0, description="Threshold for rebalancing (%)")


class SellRecommendation(BaseModel):
    """Recommendation to reduce an overweight position."""

    ticker: str
    current_pct: float
    target_pct: float
    excess_pct: float = Field(..., description="How much overweight (%)")
    rationale: str


class RebalanceResponse(BaseModel):
    """Response with rebalancing analysis."""

    is_rebalance_recommended: bool = Field(..., description="Whether rebalancing is recommended")
    max_deviation: float = Field(..., description="Maximum deviation from target (%)")
    overweight_positions: List[SellRecommendation] = Field(default_factory=list)
    underweight_positions: List[str] = Field(default_factory=list, description="Underweight tickers")
    tax_note: str = Field(
        "Consider tax implications before selling. Quarterly rebalancing is typically sufficient.",
        description="Tax reminder"
    )
