"""Pydantic models for market data."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


# Bounds for expected returns validation
EXPECTED_RETURN_MIN = -0.05  # -5%
EXPECTED_RETURN_MAX = 0.15   # +15%


class Valuation(BaseModel):
    """Valuation metrics for a region."""

    region: str = Field(..., description="Region name (US, Europe, Japan, EM)")
    cape: Optional[float] = Field(None, description="Cyclically Adjusted P/E")
    forward_pe: Optional[float] = Field(None, description="Forward P/E ratio")
    dividend_yield: float = Field(..., description="Dividend yield (as decimal)")
    source: str = Field(..., description="Data source")
    date: str = Field(..., description="Data date")
    source_date: Optional[str] = Field(None, description="Date of the source data")
    confidence: Optional[str] = Field(
        None,
        pattern="^(high|medium|low)$",
        description="Confidence level of the data"
    )


class Volatility(BaseModel):
    """Volatility metrics for an asset class."""

    asset: str = Field(..., description="Asset name")
    implied_vol: Optional[float] = Field(None, description="Implied volatility (as decimal)")
    realized_vol_1y: Optional[float] = Field(None, description="1Y realized volatility (as decimal)")
    source: str = Field(..., description="Data source")
    source_date: Optional[str] = Field(None, description="Date of the source data")
    confidence: Optional[str] = Field(
        None,
        pattern="^(high|medium|low)$",
        description="Confidence level of the data"
    )


class InstitutionalView(BaseModel):
    """Institutional view on a region/asset."""

    region: str = Field(..., description="Region or asset")
    stance: str = Field(
        ...,
        pattern="^(overweight|neutral|underweight)$",
        description="Stance",
    )
    sources: List[str] = Field(..., description="Institutions providing this view")
    key_drivers: List[str] = Field(default_factory=list, description="Key rationale")
    confidence: Optional[str] = Field(
        None,
        pattern="^(high|medium|low)$",
        description="Confidence level of the view"
    )


class ExpectedReturn(BaseModel):
    """Expected return estimate for a region."""

    region: str = Field(..., description="Region name")
    expected_return: float = Field(..., alias="return", description="Expected annual return (as decimal)")
    rationale: str = Field(..., description="Rationale for the estimate")
    confidence: Optional[str] = Field(
        None,
        pattern="^(high|medium|low)$",
        description="Confidence level of the estimate"
    )
    is_suspicious: bool = Field(
        False,
        description="True if value is outside typical range [-5%, +15%]"
    )
    warning_message: Optional[str] = Field(
        None,
        description="Warning message if value is suspicious"
    )

    class Config:
        populate_by_name = True

    @model_validator(mode="after")
    def check_bounds(self) -> "ExpectedReturn":
        """Flag values outside typical range as suspicious."""
        if not (EXPECTED_RETURN_MIN <= self.expected_return <= EXPECTED_RETURN_MAX):
            self.is_suspicious = True
            self.warning_message = (
                f"Expected return {self.expected_return:.1%} for {self.region} "
                f"is outside typical range [{EXPECTED_RETURN_MIN:.0%}, {EXPECTED_RETURN_MAX:.0%}]. "
                f"Please verify this value."
            )
        return self


class CorrelationMatrix(BaseModel):
    """Correlation matrix between asset classes."""

    assets: List[str] = Field(..., description="Asset names in order")
    matrix: List[List[float]] = Field(..., description="Correlation matrix")


class MarketData(BaseModel):
    """Complete market data package."""

    valuations: List[Valuation]
    volatility: List[Volatility]
    institutional_views: List[InstitutionalView]
    expected_returns: Optional[List[ExpectedReturn]] = Field(None, description="Expected returns by region")
    correlations: Optional[CorrelationMatrix] = Field(None, description="Correlation matrix")
    risk_free_rate: float = Field(..., description="Risk-free rate (as decimal)")
    eur_pln_rate: float = Field(..., description="EUR/PLN exchange rate")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    sources: List[str] = Field(default_factory=list)


class MarketDataRequest(BaseModel):
    """Request to gather market data."""

    force_refresh: bool = Field(False, description="Force refresh even if cached")


class ValuationThresholds(BaseModel):
    """Valuation thresholds for signals."""

    region: str
    cautious_cape: Optional[float] = None
    cautious_pe: Optional[float] = None
    favorable_cape: Optional[float] = None
    favorable_pe: Optional[float] = None


class ValuationSignal(BaseModel):
    """Valuation signal for a region."""

    region: str
    cape: Optional[float]
    forward_pe: Optional[float]
    signal: str = Field(..., pattern="^(favorable|neutral|cautious)$")
    rationale: str


class MarketDataSummary(BaseModel):
    """Summary of market data for analysis."""

    valuation_signals: List[ValuationSignal]
    institutional_consensus: Dict[str, str]
    risk_free_rate: float
    eur_pln_rate: float
    data_age_hours: float


# Default thresholds from step2 prompt
DEFAULT_THRESHOLDS = [
    ValuationThresholds(region="US", cautious_cape=35, cautious_pe=22, favorable_cape=25),
    ValuationThresholds(region="Europe", cautious_pe=16, favorable_pe=14),
    ValuationThresholds(region="Japan", cautious_cape=25, favorable_cape=18),
    ValuationThresholds(region="EM", cautious_pe=14, favorable_pe=13),
]

# Default volatilities from step2 prompt (as decimals)
DEFAULT_VOLATILITIES = {
    "US": 0.16,
    "Europe": 0.18,
    "Japan": 0.20,
    "EM": 0.22,
    "Gold": 0.15,
}

# Default dividend yields from step2 prompt (as decimals)
DEFAULT_DIVIDEND_YIELDS = {
    "US": 0.013,
    "Europe": 0.028,
    "Japan": 0.020,
    "EM": 0.025,
}
