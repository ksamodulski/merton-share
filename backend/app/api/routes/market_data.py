"""Market data API routes."""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.market_data import (
    MarketData,
    MarketDataRequest,
    MarketDataSummary,
    ValuationSignal,
    DEFAULT_THRESHOLDS,
    DEFAULT_VOLATILITIES,
    DEFAULT_DIVIDEND_YIELDS,
)

router = APIRouter()

# Simple in-memory cache for market data
_market_data_cache: MarketData | None = None
_cache_timestamp: datetime | None = None

settings = get_settings()


@router.post("/gather", response_model=MarketData)
async def gather_market_data(request: MarketDataRequest) -> MarketData:
    """
    Gather current market data using Claude API.

    Collects:
    - Valuations (CAPE, Forward P/E, Dividend Yield) for US, Europe, Japan, EM
    - Volatility (implied and realized) for major indices
    - Institutional views from major firms
    - Current rates (risk-free rate, EUR/PLN)
    """
    global _market_data_cache, _cache_timestamp

    # Check cache
    if not request.force_refresh and _market_data_cache and _cache_timestamp:
        age_hours = (datetime.utcnow() - _cache_timestamp).total_seconds() / 3600
        if age_hours < settings.market_data_cache_hours:
            return _market_data_cache

    # TODO: Implement Claude-based market data gathering
    # For now, return placeholder with defaults
    # This will be implemented in Phase 3 with the market data service

    raise HTTPException(
        status_code=501,
        detail="Market data gathering not yet implemented. Use /defaults endpoint for fallback values.",
    )


@router.get("/cached")
async def get_cached_market_data() -> dict:
    """
    Get cached market data if available.
    """
    global _market_data_cache, _cache_timestamp

    if not _market_data_cache:
        return {
            "cached": False,
            "message": "No cached market data available",
        }

    age_hours = (
        (datetime.utcnow() - _cache_timestamp).total_seconds() / 3600
        if _cache_timestamp
        else 0
    )

    return {
        "cached": True,
        "data": _market_data_cache,
        "age_hours": round(age_hours, 2),
        "is_stale": age_hours > settings.market_data_cache_hours,
    }


@router.get("/defaults")
async def get_default_values() -> dict:
    """
    Get default fallback values for market data.

    These are from the step2 prompt and should be used when
    live data is not available.
    """
    return {
        "volatilities": DEFAULT_VOLATILITIES,
        "dividend_yields": DEFAULT_DIVIDEND_YIELDS,
        "thresholds": [t.model_dump() for t in DEFAULT_THRESHOLDS],
        "default_risk_free_rate": 0.025,  # 2.5%
    }


@router.post("/signals")
async def calculate_valuation_signals(
    valuations: dict,
    thresholds: dict | None = None,
) -> list[ValuationSignal]:
    """
    Calculate valuation signals based on thresholds.

    Signals:
    - favorable: Below favorable threshold
    - neutral: Between thresholds
    - cautious: Above cautious threshold
    """
    signals = []

    # Use default thresholds if not provided
    threshold_map = {}
    for t in DEFAULT_THRESHOLDS:
        threshold_map[t.region] = t
    if thresholds:
        for region, thresh in thresholds.items():
            if region in threshold_map:
                threshold_map[region] = thresh

    for region, data in valuations.items():
        cape = data.get("cape")
        pe = data.get("forward_pe")
        thresh = threshold_map.get(region)

        signal = "neutral"
        rationale = []

        if thresh:
            # Check cautious conditions
            if cape and thresh.cautious_cape and cape > thresh.cautious_cape:
                signal = "cautious"
                rationale.append(f"CAPE {cape} > {thresh.cautious_cape}")
            elif pe and thresh.cautious_pe and pe > thresh.cautious_pe:
                signal = "cautious"
                rationale.append(f"P/E {pe} > {thresh.cautious_pe}")
            # Check favorable conditions (only if not already cautious)
            elif cape and thresh.favorable_cape and cape < thresh.favorable_cape:
                signal = "favorable"
                rationale.append(f"CAPE {cape} < {thresh.favorable_cape}")
            elif pe and thresh.favorable_pe and pe < thresh.favorable_pe:
                signal = "favorable"
                rationale.append(f"P/E {pe} < {thresh.favorable_pe}")

        signals.append(
            ValuationSignal(
                region=region,
                cape=cape,
                forward_pe=pe,
                signal=signal,
                rationale=", ".join(rationale) if rationale else "Within normal range",
            )
        )

    return signals
