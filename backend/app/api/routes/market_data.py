"""Market data API routes."""

import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models.market_data import (
    MarketData,
    MarketDataRequest,
    MarketDataSummary,
    Valuation,
    Volatility,
    InstitutionalView,
    ExpectedReturn,
    CorrelationMatrix,
    ValuationSignal,
    DEFAULT_THRESHOLDS,
    DEFAULT_VOLATILITIES,
    DEFAULT_DIVIDEND_YIELDS,
)
from app.services.claude_service import get_claude_service
from app.core.view_mapping import apply_view_adjustments

router = APIRouter()

# Simple in-memory cache for market data
_market_data_cache: MarketData | None = None
_cache_timestamp: datetime | None = None

settings = get_settings()


def _assemble_market_data(result: dict, user_views: dict | None) -> MarketData:
    """Convert Claude's raw JSON into a MarketData model, applying view blends.

    Shared by the blocking ``/gather`` endpoint and the streaming
    ``/gather/stream`` endpoint so the post-processing stays identical.
    """
    valuations = [
        Valuation(
            region=v["region"],
            cape=v.get("cape"),
            forward_pe=v.get("forward_pe"),
            dividend_yield=v.get("dividend_yield", 0.02),
            source=v.get("source", "Claude"),
            date=v.get("date", datetime.utcnow().date().isoformat()),
        )
        for v in result.get("valuations", [])
    ]

    volatility = [
        Volatility(
            asset=v["asset"],
            implied_vol=v.get("implied_vol"),
            realized_vol_1y=v.get("realized_vol_1y"),
            source=v.get("source", "Claude"),
        )
        for v in result.get("volatility", [])
    ]

    institutional_views = [
        InstitutionalView(
            region=v["region"],
            stance=v.get("stance", "neutral"),
            sources=v.get("sources", ["Claude"]),
            key_drivers=v.get("key_drivers", []),
            confidence=v.get("confidence"),
        )
        for v in result.get("institutional_views", [])
    ]

    # Build dicts for view adjustment lookup
    inst_stances = {v.region: v.stance for v in institutional_views}
    inst_confidence = {v.region: v.confidence for v in institutional_views}

    # Parse expected returns from Claude and apply confidence-scaled view adjustments
    raw_returns = result.get("expected_returns", [])
    expected_returns = None
    if raw_returns:
        base_returns = {r["region"]: r.get("return", 0.05) for r in raw_returns}
        view_adjustments = apply_view_adjustments(
            base_returns=base_returns,
            institutional_views=inst_stances,
            confidence=inst_confidence,
            user_views=user_views,
            enabled=True,
        )
        expected_returns = []
        for r in raw_returns:
            region = r["region"]
            adj = view_adjustments.get(region)
            adjusted_value = adj.adjusted_return if adj else r.get("return", 0.05)
            rationale = r.get("rationale", "")
            if adj and adj.adjustment != 0:
                rationale += f" + view adj {adj.adjustment:+.1%} ({adj.rationale})"
            expected_returns.append(
                ExpectedReturn.model_validate({
                    "region": region,
                    "return": adjusted_value,
                    "rationale": rationale,
                    "confidence": r.get("confidence"),
                })
            )

    # Parse correlation matrix if provided
    correlations_raw = result.get("correlations")
    correlations = None
    if correlations_raw and "assets" in correlations_raw and "matrix" in correlations_raw:
        correlations = CorrelationMatrix(
            assets=correlations_raw["assets"],
            matrix=correlations_raw["matrix"],
        )

    return MarketData(
        valuations=valuations,
        volatility=volatility,
        institutional_views=institutional_views,
        expected_returns=expected_returns,
        correlations=correlations,
        risk_free_rate=result.get("risk_free_rate", 0.025),
        bund_yield_10y=result.get("bund_yield_10y"),
        eur_pln_rate=result.get("eur_pln_rate", 4.30),
        fetched_at=datetime.utcnow(),
        sources=result.get("sources", ["Claude API"]),
    )


@router.post("/gather", response_model=MarketData)
async def gather_market_data(request: MarketDataRequest) -> MarketData:
    """
    Gather current market data using Claude API.

    Collects:
    - Valuations (CAPE, Forward P/E, Dividend Yield) for US, Europe, Japan, EM, Pacific
    - Volatility (implied and realized) for major indices
    - Institutional views from major firms
    - Current rates (risk-free rate, EUR/PLN)
    """
    global _market_data_cache, _cache_timestamp

    # Check cache (skip when the user supplied their own views, since those
    # change the blended expected returns and the cache is view-agnostic).
    if not request.force_refresh and not request.user_views and _market_data_cache and _cache_timestamp:
        age_hours = (datetime.utcnow() - _cache_timestamp).total_seconds() / 3600
        if age_hours < settings.market_data_cache_hours:
            return _market_data_cache

    try:
        # Gather market data using Claude
        claude = get_claude_service()
        result = await claude.gather_market_data()

        market_data = _assemble_market_data(result, request.user_views)

        # Cache the result (only the view-agnostic version, so user-specific
        # blends never leak into a later request that omits user views).
        if not request.user_views:
            _market_data_cache = market_data
            _cache_timestamp = datetime.utcnow()

        return market_data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to gather market data: {str(e)}",
        )


@router.post("/gather/stream")
async def gather_market_data_stream(request: MarketDataRequest) -> StreamingResponse:
    """
    Streaming variant of ``/gather``.

    Emits Server-Sent Events so the UI can show live progress:
      data: {"type": "status", "stage": ..., "detail": ...}
      data: {"type": "result", "data": <MarketData>}
      data: {"type": "error",  "detail": ...}
    """

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    async def event_gen():
        global _market_data_cache, _cache_timestamp

        # Serve from cache when allowed (the UI normally forces a refresh).
        if (not request.force_refresh and not request.user_views
                and _market_data_cache and _cache_timestamp):
            age_hours = (datetime.utcnow() - _cache_timestamp).total_seconds() / 3600
            if age_hours < settings.market_data_cache_hours:
                yield sse({"type": "status", "stage": "cache", "detail": "Loaded from cache"})
                yield sse({"type": "result", "data": jsonable_encoder(_market_data_cache)})
                return

        claude = get_claude_service()
        raw_result = None
        try:
            async for ev in claude.gather_market_data_streaming():
                if ev.get("type") == "result":
                    raw_result = ev["data"]
                    break
                if ev.get("type") == "error":
                    yield sse(ev)
                    return
                yield sse(ev)
        except Exception as e:  # noqa: BLE001 — surfaced to the client as an error event
            yield sse({"type": "error", "detail": f"Failed to gather market data: {e}"})
            return

        if raw_result is None:
            yield sse({"type": "error", "detail": "No data returned from Claude"})
            return

        try:
            market_data = _assemble_market_data(raw_result, request.user_views)
        except Exception as e:  # noqa: BLE001
            yield sse({"type": "error", "detail": f"Failed to assemble market data: {e}"})
            return

        if not request.user_views:
            _market_data_cache = market_data
            _cache_timestamp = datetime.utcnow()

        yield sse({"type": "result", "data": jsonable_encoder(market_data)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


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
