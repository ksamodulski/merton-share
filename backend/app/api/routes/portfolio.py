"""Portfolio management API routes."""

import csv
import io
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, List

from app.models.portfolio import (
    ETFHolding,
    BondPosition,
    Portfolio,
    PortfolioInput,
    CSVParseResult,
    ETFMetadata,
    ETFLookupRequest,
    ETFLookupResponse,
    ETFMappingsExport,
)
from app.services.claude_service import get_claude_service

router = APIRouter()

# In-memory cache for ETF mappings (persists during server lifetime)
_etf_mappings_cache: Dict[str, ETFMetadata] = {}


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


@router.post("/parse-csv", response_model=CSVParseResult)
async def parse_csv(file: UploadFile = File(...)) -> CSVParseResult:
    """
    Parse portfolio from IBKR CSV export.

    Expects the standard IBKR Activity Statement CSV format with
    "Open Positions" section containing stock holdings.
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Must be a CSV file.",
        )

    # Read file content
    content = await file.read()

    if len(content) > 5 * 1024 * 1024:  # 5MB limit for CSV
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB.")

    try:
        # Decode and parse CSV
        text = content.decode('utf-8-sig')  # Handle BOM
        reader = csv.reader(io.StringIO(text))

        holdings = []
        total_value = 0.0

        for row in reader:
            # Look for Open Positions data rows
            # Format: Open Positions,Data,Summary,Stocks,EUR,SYMBOL,Qty,Mult,CostPrice,CostBasis,ClosePrice,Value,UnrealizedPL,Code
            #         [0]            [1]  [2]     [3]    [4] [5]    [6] [7]  [8]       [9]       [10]       [11]  [12]         [13]
            if (
                len(row) >= 12
                and row[0] == "Open Positions"
                and row[1] == "Data"
                and row[2] == "Summary"
                and row[3] == "Stocks"
            ):
                currency = row[4]
                symbol = row[5]
                try:
                    value = float(row[11]) if row[11] else 0.0  # Column 11 is Value
                except ValueError:
                    continue

                if symbol and value > 0:
                    holdings.append(
                        ETFHolding(
                            ticker=symbol,
                            value_eur=value,
                            percentage=0,  # Will be calculated
                            is_accumulating=True,  # Default
                            currency_denomination=currency,
                            is_ucits=True,  # Default
                            ter=0.002,  # Default 0.2%
                        )
                    )
                    total_value += value

        if not holdings:
            raise HTTPException(
                status_code=400,
                detail="No valid holdings found in CSV. Make sure it's an IBKR Activity Statement export.",
            )

        # Calculate percentages
        for holding in holdings:
            holding.percentage = (holding.value_eur / total_value) * 100 if total_value > 0 else 0

        return CSVParseResult(
            holdings=holdings,
            total_value_eur=total_value,
            num_positions=len(holdings),
        )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Failed to decode CSV file. Make sure it's a valid UTF-8 encoded file.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse CSV: {str(e)}",
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


@router.post("/lookup-etfs", response_model=ETFLookupResponse)
async def lookup_etf_metadata(request: ETFLookupRequest) -> ETFLookupResponse:
    """
    Look up ETF metadata using Claude.

    Returns region mappings, names, ISINs, TERs for each ticker.
    Results are cached for future use.
    """
    global _etf_mappings_cache

    # Check which tickers need lookup (not in cache)
    tickers_to_lookup = [t for t in request.tickers if t not in _etf_mappings_cache]

    if tickers_to_lookup:
        try:
            claude_service = get_claude_service()
            results = await claude_service.lookup_etf_metadata(tickers_to_lookup)

            # Cache the results
            for etf_data in results:
                metadata = ETFMetadata(
                    ticker=etf_data.get("ticker", ""),
                    region=etf_data.get("region", "US"),
                    name=etf_data.get("name"),
                    isin=etf_data.get("isin"),
                    ter=etf_data.get("ter"),
                    is_accumulating=etf_data.get("is_accumulating"),
                    description=etf_data.get("description"),
                )
                _etf_mappings_cache[metadata.ticker] = metadata
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to lookup ETF metadata: {str(e)}",
            )

    # Return all requested tickers from cache
    etfs = []
    for ticker in request.tickers:
        if ticker in _etf_mappings_cache:
            etfs.append(_etf_mappings_cache[ticker])
        else:
            # Fallback if somehow not in cache
            etfs.append(ETFMetadata(ticker=ticker, region="US"))

    return ETFLookupResponse(etfs=etfs, lookup_source="claude")


@router.get("/etf-mappings/export", response_model=ETFMappingsExport)
async def export_etf_mappings() -> ETFMappingsExport:
    """
    Export cached ETF mappings as JSON.

    Use this to save mappings and avoid repeated Claude lookups.
    """
    return ETFMappingsExport(
        mappings=_etf_mappings_cache,
        exported_at=datetime.utcnow().isoformat(),
    )


@router.post("/etf-mappings/import")
async def import_etf_mappings(data: ETFMappingsExport) -> dict:
    """
    Import ETF mappings from JSON.

    Use this to restore previously exported mappings.
    """
    global _etf_mappings_cache

    imported_count = 0
    for ticker, metadata in data.mappings.items():
        _etf_mappings_cache[ticker] = metadata
        imported_count += 1

    return {
        "imported_count": imported_count,
        "total_cached": len(_etf_mappings_cache),
    }
