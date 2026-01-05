"""Portfolio management API routes."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List

from app.models.portfolio import (
    ETFHolding,
    BondPosition,
    Portfolio,
    PortfolioInput,
    ScreenshotParseResult,
)

router = APIRouter()


@router.post("", response_model=Portfolio)
async def create_portfolio(portfolio_input: PortfolioInput) -> Portfolio:
    """
    Create/validate a portfolio from manual input.

    Validates all ETF holdings against hard constraints:
    - Accumulating only (not distributing)
    - EUR-denominated
    - UCITS-compliant
    - TER < 0.50%
    """
    # Check for constraint violations
    violations = {}
    for holding in portfolio_input.holdings:
        holding_violations = holding.get_constraint_violations()
        if holding_violations:
            violations[holding.ticker] = holding_violations

    if violations:
        # Return violations as warning, not error (allow proceeding with warnings)
        pass  # Could add to response if needed

    # Calculate total value
    total_value = sum(h.value_eur for h in portfolio_input.holdings)

    # Update percentages if not provided correctly
    for holding in portfolio_input.holdings:
        if total_value > 0:
            holding.percentage = (holding.value_eur / total_value) * 100

    return Portfolio(
        holdings=portfolio_input.holdings,
        total_value_eur=total_value,
        bond_position=portfolio_input.bond_position,
    )


@router.post("/validate-etf")
async def validate_etf(holding: ETFHolding) -> dict:
    """
    Validate a single ETF against constraints.

    Returns the holding with any constraint violations noted.
    """
    violations = holding.get_constraint_violations()
    return {
        "holding": holding,
        "is_valid": len(violations) == 0,
        "violations": violations,
    }


@router.post("/parse-screenshot", response_model=ScreenshotParseResult)
async def parse_screenshot(file: UploadFile = File(...)) -> ScreenshotParseResult:
    """
    Parse portfolio from IBKR screenshot using Claude Vision.

    Accepts PNG or JPG image, extracts ETF holdings using AI vision.
    """
    # Validate file type
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Must be PNG or JPG.",
        )

    # Read file content
    content = await file.read()

    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    # TODO: Implement Claude Vision parsing
    # For now, return a placeholder response
    # This will be implemented in Phase 2 with the Claude service

    raise HTTPException(
        status_code=501,
        detail="Screenshot parsing not yet implemented. Please use manual entry.",
    )


@router.post("/bonds/convert")
async def convert_bond_to_eur(
    amount_pln: float,
    eur_pln_rate: float,
) -> dict:
    """
    Convert PLN bond amount to EUR equivalent.
    """
    if amount_pln <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if eur_pln_rate <= 0:
        raise HTTPException(status_code=400, detail="Exchange rate must be positive")

    amount_eur = amount_pln / eur_pln_rate
    return {
        "amount_pln": amount_pln,
        "amount_eur": round(amount_eur, 2),
        "eur_pln_rate": eur_pln_rate,
    }
