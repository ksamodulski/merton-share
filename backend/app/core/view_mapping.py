"""
Qualitative to Quantitative View Mapping (Black-Litterman Lite).

Maps institutional views (overweight/neutral/underweight) to return adjustments.
This is a simplified approach inspired by Black-Litterman, where qualitative
views are converted to numeric adjustments on expected returns.

The full Black-Litterman model blends views with equilibrium returns using
a Bayesian framework. This simplified version applies additive adjustments
based on view strength and confidence.

Usage:
    from app.core.view_mapping import apply_view_adjustments

    adjusted = apply_view_adjustments(
        base_returns={"US": 0.05, "Europe": 0.07},
        institutional_views={"US": "overweight", "Europe": "neutral"},
        enabled=True
    )
"""

from typing import Dict, Optional
from dataclasses import dataclass

# Return adjustment bounds (same as validation bounds)
RETURN_MIN = -0.05  # -5%
RETURN_MAX = 0.15   # +15%


@dataclass
class ViewAdjustment:
    """Result of applying view adjustments to a single region."""

    region: str
    base_return: float
    adjustment: float
    adjusted_return: float
    sources: list[str]
    rationale: str
    confidence: Optional[str] = None  # high/medium/low confidence of the view


# Scale factor applied to the base adjustment depending on confidence.
# "high"   → web-searched, breaking news  → full ±2%
# "medium" → recent reports or derived    → ±1.5%
# "low"    → pure Claude estimate         → ±1%
# None     → treated the same as "low"
CONFIDENCE_SCALE: Dict[Optional[str], float] = {
    "high":   1.0,
    "medium": 0.75,
    "low":    0.5,
    None:     0.5,
}

# Base adjustments before scaling by confidence (in decimal)
BASE_VIEW_ADJUSTMENT: Dict[str, float] = {
    "overweight":  +0.02,   # up to +2% return premium
    "neutral":      0.0,
    "underweight": -0.02,   # up to -2% return penalty
}

# Default confidence assigned to the *user's own* views. The user does not
# enter a confidence in the UI (3-way stance only), so we treat their explicit
# conviction as high — i.e. at least as strong as institutional consensus when
# the two are blended. Lower this constant to make user views less dominant.
USER_VIEW_DEFAULT_CONFIDENCE = "high"

# Optional: Valuation signal adjustments (smaller magnitude)
VALUATION_SIGNAL_ADJUSTMENT = {
    "favorable": +0.005,    # +0.5% for attractive valuations
    "neutral": 0.0,
    "cautious": -0.01,      # -1% for stretched valuations
}


def apply_view_adjustments(
    base_returns: Dict[str, float],
    institutional_views: Optional[Dict[str, str]] = None,
    valuation_signals: Optional[Dict[str, str]] = None,
    confidence: Optional[Dict[str, Optional[str]]] = None,
    user_views: Optional[Dict[str, str]] = None,
    user_confidence: Optional[Dict[str, Optional[str]]] = None,
    enabled: bool = False,
) -> Dict[str, ViewAdjustment]:
    """
    Apply qualitative view adjustments to base expected returns.

    This function implements a simplified Black-Litterman approach where
    institutional views, the user's own views, and valuation signals are
    converted to numeric adjustments on expected returns.

    Institutional and user stances (±2% at full strength) are combined into a
    single confidence-weighted blend per region: each source contributes its
    base magnitude weighted by its confidence scale, and the remaining weight
    mass implicitly goes to equilibrium (neutral, 0) — which is why the
    denominator is floored at 1.0. With a single source this reduces to the
    original ``magnitude * confidence_scale`` behaviour; with both sources a
    high-confidence user view outweighs a low-confidence institutional one.
    Confidence scales:
      - high   (web-searched breaking news / explicit user view) → weight 1.0
      - medium (recent reports / derived)                        → weight 0.75
      - low    (pure Claude estimate)                            → weight 0.5

    Args:
        base_returns: Dict of region -> base expected return (decimal)
        institutional_views: Dict of region -> stance (overweight/neutral/underweight)
        valuation_signals: Dict of region -> signal (favorable/neutral/cautious)
        confidence: Dict of region -> confidence level (high/medium/low/None)
        user_views: Dict of region -> user's own stance (overweight/neutral/underweight).
            Only include regions the user explicitly expressed an opinion on.
        user_confidence: Optional dict of region -> confidence for user views;
            defaults to USER_VIEW_DEFAULT_CONFIDENCE ("high") when absent.
        enabled: If False, returns base returns without adjustment

    Returns:
        Dict of region -> ViewAdjustment containing adjusted returns

    Example:
        >>> base = {"US": 0.05, "Europe": 0.07}
        >>> views = {"US": "overweight", "Europe": "underweight"}
        >>> conf  = {"US": "high", "Europe": "low"}
        >>> result = apply_view_adjustments(base, views, confidence=conf, enabled=True)
        >>> result["US"].adjusted_return
        0.07   # 5% + 2% (high-confidence overweight)
        >>> result["Europe"].adjusted_return
        0.06   # 7% - 1% (low-confidence underweight)
    """
    adjustments = {}

    for region, base_return in base_returns.items():
        inst_adj = 0.0
        val_adj = 0.0
        rationale_parts = []
        sources = []
        region_confidence: Optional[str] = None

        # Blend institutional + user stances by confidence (Black-Litterman lite).
        # Each present source contributes (confidence_weight * base_magnitude);
        # the denominator is floored at 1.0 so a single source reduces to the
        # original magnitude*confidence behaviour while two sources average out.
        weighted_sum = 0.0
        weight_total = 0.0

        if enabled and institutional_views and region in institutional_views:
            stance = institutional_views[region]
            region_confidence = (confidence or {}).get(region)
            w = CONFIDENCE_SCALE.get(region_confidence, CONFIDENCE_SCALE[None])
            m = BASE_VIEW_ADJUSTMENT.get(stance, 0.0)
            weighted_sum += w * m
            weight_total += w
            if m != 0:
                rationale_parts.append(
                    f"institutional {stance} (conf:{region_confidence or 'low'})"
                )
                sources.append("Institutional consensus")

        if enabled and user_views and region in user_views:
            u_stance = user_views[region]
            u_conf = (user_confidence or {}).get(region) or USER_VIEW_DEFAULT_CONFIDENCE
            w = CONFIDENCE_SCALE.get(u_conf, CONFIDENCE_SCALE[None])
            m = BASE_VIEW_ADJUSTMENT.get(u_stance, 0.0)
            weighted_sum += w * m
            weight_total += w
            # A user "neutral" (m==0) still carries weight and dampens the
            # institutional stance toward equilibrium, so record it either way.
            rationale_parts.append(f"your view {u_stance} (conf:{u_conf})")
            sources.append("Your view")

        if weight_total > 0:
            inst_adj = weighted_sum / max(1.0, weight_total)

        # Apply valuation signal adjustment if enabled
        if enabled and valuation_signals and region in valuation_signals:
            signal = valuation_signals[region]
            val_adj = VALUATION_SIGNAL_ADJUSTMENT.get(signal, 0.0)
            if val_adj != 0:
                direction = "+" if val_adj > 0 else ""
                rationale_parts.append(
                    f"valuation {signal} ({direction}{val_adj:.1%})"
                )
                sources.append("Valuation analysis")

        # Calculate total adjustment
        total_adjustment = inst_adj + val_adj

        # Calculate adjusted return (clamped to valid bounds)
        adjusted_return = base_return + total_adjustment if enabled else base_return
        adjusted_return = max(RETURN_MIN, min(RETURN_MAX, adjusted_return))

        adjustments[region] = ViewAdjustment(
            region=region,
            base_return=base_return,
            adjustment=total_adjustment if enabled else 0.0,
            adjusted_return=adjusted_return,
            sources=sources if sources else ["No adjustment applied"],
            rationale=" + ".join(rationale_parts) if rationale_parts else "Base return (no view adjustment)",
            confidence=region_confidence,
        )

    return adjustments


def get_adjusted_returns(
    base_returns: Dict[str, float],
    institutional_views: Optional[Dict[str, str]] = None,
    valuation_signals: Optional[Dict[str, str]] = None,
    confidence: Optional[Dict[str, Optional[str]]] = None,
    user_views: Optional[Dict[str, str]] = None,
    user_confidence: Optional[Dict[str, Optional[str]]] = None,
    enabled: bool = False,
) -> Dict[str, float]:
    """
    Convenience function that returns just the adjusted return values.

    Args:
        base_returns: Dict of region -> base expected return
        institutional_views: Dict of region -> stance
        valuation_signals: Dict of region -> signal
        confidence: Dict of region -> confidence level (high/medium/low/None)
        enabled: If False, returns base returns without adjustment

    Returns:
        Dict of region -> adjusted return (decimal)
    """
    adjustments = apply_view_adjustments(
        base_returns=base_returns,
        institutional_views=institutional_views,
        valuation_signals=valuation_signals,
        confidence=confidence,
        user_views=user_views,
        user_confidence=user_confidence,
        enabled=enabled,
    )
    return {region: adj.adjusted_return for region, adj in adjustments.items()}
