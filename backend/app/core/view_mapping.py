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
    enabled: bool = False,
) -> Dict[str, ViewAdjustment]:
    """
    Apply qualitative view adjustments to base expected returns.

    This function implements a simplified Black-Litterman approach where
    institutional views and valuation signals are converted to numeric
    adjustments on expected returns. The adjustment magnitude is scaled
    by the confidence level of each view:
      - high   (web-searched breaking news) → ±2.0%
      - medium (recent reports / derived)   → ±1.5%
      - low    (pure Claude estimate)       → ±1.0%

    Args:
        base_returns: Dict of region -> base expected return (decimal)
        institutional_views: Dict of region -> stance (overweight/neutral/underweight)
        valuation_signals: Dict of region -> signal (favorable/neutral/cautious)
        confidence: Dict of region -> confidence level (high/medium/low/None)
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

        # Apply institutional view adjustment if enabled
        if enabled and institutional_views and region in institutional_views:
            stance = institutional_views[region]
            region_confidence = (confidence or {}).get(region)
            scale = CONFIDENCE_SCALE.get(region_confidence, CONFIDENCE_SCALE[None])
            inst_adj = BASE_VIEW_ADJUSTMENT.get(stance, 0.0) * scale
            if inst_adj != 0:
                conf_label = region_confidence or "low"
                direction = "+" if inst_adj > 0 else ""
                rationale_parts.append(
                    f"institutional {stance} (conf:{conf_label}, {direction}{inst_adj:.1%})"
                )
                sources.append("Institutional consensus")

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
        enabled=enabled,
    )
    return {region: adj.adjusted_return for region, adj in adjustments.items()}
