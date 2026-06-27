"""Market data API routes."""

import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models.market_data import (
    MarketData,
    MarketDataRequest,
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
from app.services import market_data_cache as cache
from app.services import market_data_job as jobs
from app.core.view_mapping import apply_view_adjustments

router = APIRouter()

settings = get_settings()


def _assemble_market_data(result: dict, user_views: dict | None) -> MarketData:
    """Convert Claude's raw JSON into a MarketData model, applying view blends.

    Pure post-processing over the raw fetch, so it can be re-run cheaply with
    different ``user_views`` without re-calling Claude.
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


def _cache_is_fresh() -> bool:
    age = cache.age_hours()
    return age is not None and age < settings.market_data_cache_hours


@router.post("/gather", response_model=MarketData)
async def gather_market_data(request: MarketDataRequest) -> MarketData:
    """
    Gather current market data using Claude API (blocking).

    Runs via the shared background job so a concurrent streaming client sees the
    same run, and the result is persisted for restart survival.
    """
    raw, _ = cache.get()

    # Serve cache when allowed (view blends are re-applied on top regardless).
    if not request.force_refresh and _cache_is_fresh() and raw is not None:
        return _assemble_market_data(raw, request.user_views)

    try:
        job = jobs.start()
        if job.task is not None:
            await job.task
        if job.status == "error":
            raise RuntimeError(job.error or "Fetch failed")
        if job.status == "cancelled":
            raise RuntimeError("Fetch was cancelled")
        if job.raw_result is None:
            raise RuntimeError("No data returned from Claude")
        return _assemble_market_data(job.raw_result, request.user_views)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to gather market data: {str(e)}",
        )


@router.post("/gather/stream")
async def gather_market_data_stream(request: MarketDataRequest) -> StreamingResponse:
    """
    Streaming variant of ``/gather`` backed by a server-side background job.

    The actual Claude fetch runs in a detached task (see ``market_data_job``),
    so a client disconnect (refresh/tab close) only stops *this* viewer — the
    job keeps running and persists its result. Emits Server-Sent Events:
      data: {"type": "status", "stage": ..., "detail": ..., "at": ...}
      data: {"type": "result", "data": <MarketData>}
      data: {"type": "error",  "detail": ...}
      data: {"type": "idle"}   # attach_only and nothing running/cached
    """

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    async def event_gen():
        raw, _ = cache.get()

        # Serve cache when allowed (the UI normally forces a refresh).
        if not request.force_refresh and _cache_is_fresh() and raw is not None:
            yield sse({"type": "status", "stage": "cache", "detail": "Loaded from cache"})
            yield sse({"type": "result",
                       "data": jsonable_encoder(_assemble_market_data(raw, request.user_views))})
            return

        job = jobs.current()
        if job is None or job.status != "running":
            if request.attach_only:
                # Don't start a paid fetch on a passive re-attach. Hand back the
                # last result if we have one, else signal idle.
                if raw is not None:
                    yield sse({"type": "result",
                               "data": jsonable_encoder(_assemble_market_data(raw, request.user_views))})
                else:
                    yield sse({"type": "idle"})
                return
            job = jobs.start()

        # Replay buffered progress, then stream live until the job finishes.
        async for ev in jobs.stream_events(job):
            yield sse(ev)

        if job.status == "done" and job.raw_result is not None:
            yield sse({"type": "result",
                       "data": jsonable_encoder(_assemble_market_data(job.raw_result, request.user_views))})
        elif job.status == "cancelled":
            yield sse({"type": "error", "detail": "Fetch was cancelled"})
        else:
            yield sse({"type": "error", "detail": job.error or "Fetch failed"})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/gather/status")
async def gather_status() -> dict:
    """Lightweight status of the background fetch — for the UI's live indicator
    (and quick checks via curl)."""
    job = jobs.current()
    age = cache.age_hours()
    return {
        "running": jobs.is_running(),
        "job_id": job.id if job else None,
        "status": job.status if job else None,
        "started_at": job.started_at.isoformat() if job else None,
        "elapsed_seconds": job.elapsed_seconds if job else None,
        "events": job.events if job else [],
        "error": job.error if job else None,
        "has_cache": age is not None,
        "cache_age_hours": round(age, 2) if age is not None else None,
        "cache_is_stale": (age is not None and age > settings.market_data_cache_hours),
    }


@router.post("/gather/cancel")
async def gather_cancel() -> dict:
    """Cancel the running background fetch, if any."""
    cancelled = await jobs.cancel()
    return {"cancelled": cancelled}


@router.get("/cached")
async def get_cached_market_data() -> dict:
    """
    Get cached market data if available.
    """
    raw, ts = cache.get()
    if raw is None:
        return {
            "cached": False,
            "message": "No cached market data available",
        }

    age = cache.age_hours() or 0
    return {
        "cached": True,
        "data": _assemble_market_data(raw, None),
        "age_hours": round(age, 2),
        "is_stale": age > settings.market_data_cache_hours,
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
