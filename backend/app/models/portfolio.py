"""Pydantic models for portfolio data."""

from datetime import date
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ETFHolding(BaseModel):
    """Model for a single ETF holding."""

    ticker: str = Field(..., min_length=1, description="ETF ticker symbol")
    isin: Optional[str] = Field(None, description="ISIN identifier")
    name: Optional[str] = Field(None, description="Full ETF name")
    region: Optional[str] = Field(None, description="Asset region: US, Europe, Japan, EM, Gold")
    value_eur: float = Field(..., gt=0, description="Current value in EUR")
    percentage: float = Field(
        ..., ge=0, le=100, description="Percentage of portfolio"
    )
    is_accumulating: bool = Field(True, description="True if accumulating (not distributing)")
    currency_denomination: str = Field("EUR", description="Currency denomination")
    is_ucits: bool = Field(True, description="UCITS compliant")
    ter: float = Field(..., ge=0, lt=1, description="Total Expense Ratio (as decimal)")

    @field_validator("ter")
    @classmethod
    def validate_ter(cls, v: float) -> float:
        """Warn if TER exceeds 0.50% threshold."""
        # We don't raise an error here, just validate.
        # Constraint violations are tracked separately.
        return v

    def get_constraint_violations(self) -> List[str]:
        """Check for hard constraint violations."""
        violations = []
        if not self.is_accumulating:
            violations.append("Must be accumulating (not distributing)")
        if self.currency_denomination != "EUR":
            violations.append(f"Must be EUR-denominated (got {self.currency_denomination})")
        if not self.is_ucits:
            violations.append("Must be UCITS-compliant")
        if self.ter > 0.005:  # 0.50%
            violations.append(f"TER {self.ter*100:.2f}% exceeds 0.50% limit")
        return violations


class BondPosition(BaseModel):
    """Model for bond position (Polish inflation-linked bonds)."""

    amount_pln: float = Field(..., gt=0, description="Amount in PLN")
    yield_rate: float = Field(
        ..., ge=0, le=0.20, description="Annual yield rate (as decimal)"
    )
    lock_date: date = Field(..., description="Lock-until date")
    amount_eur: Optional[float] = Field(
        None, description="Calculated EUR equivalent"
    )


class Portfolio(BaseModel):
    """Model for complete portfolio."""

    holdings: List[ETFHolding] = Field(..., min_length=0)
    total_value_eur: float = Field(..., ge=0, description="Total portfolio value in EUR")
    bond_position: Optional[BondPosition] = None

    def get_total_with_bonds(self, eur_pln_rate: float) -> float:
        """Calculate total value including bonds in EUR."""
        bond_value = 0.0
        if self.bond_position:
            bond_value = self.bond_position.amount_pln / eur_pln_rate
        return self.total_value_eur + bond_value


class PortfolioInput(BaseModel):
    """Model for manual portfolio entry."""

    holdings: List[ETFHolding]
    bond_position: Optional[BondPosition] = None


class CSVParseResult(BaseModel):
    """Result from parsing IBKR CSV export."""

    holdings: List[ETFHolding]
    total_value_eur: float
    num_positions: int = Field(..., description="Number of positions parsed")


class ETFMetadata(BaseModel):
    """Metadata for an ETF from Claude lookup."""

    ticker: str = Field(..., description="ETF ticker symbol")
    region: str = Field(..., description="Asset region: US, Europe, Japan, EM, Gold")
    name: Optional[str] = Field(None, description="Full ETF name")
    isin: Optional[str] = Field(None, description="ISIN identifier")
    ter: Optional[float] = Field(None, ge=0, lt=1, description="Total Expense Ratio")
    is_accumulating: Optional[bool] = Field(None, description="True if accumulating")
    description: Optional[str] = Field(None, description="Brief description")


class ETFLookupRequest(BaseModel):
    """Request for ETF metadata lookup."""

    tickers: List[str] = Field(..., min_length=1, description="List of ticker symbols")


class ETFLookupResponse(BaseModel):
    """Response from ETF metadata lookup."""

    etfs: List[ETFMetadata]
    lookup_source: str = Field("claude", description="Source of lookup data")


class ETFMappingsExport(BaseModel):
    """Export format for ETF mappings."""

    mappings: Dict[str, ETFMetadata]
    exported_at: str = Field(..., description="ISO timestamp of export")
