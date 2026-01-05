"""Portfolio optimization API routes."""

from fastapi import APIRouter, HTTPException

from app.core.merton_share import PortfolioOptimizer
from app.models.optimization import (
    OptimizationRequest,
    OptimizationResponse,
    PortfolioStats,
    GapAnalysisRequest,
    GapAnalysisResponse,
    GapAnalysisRow,
    AllocationRequest,
    AllocationResponse,
    AllocationRecommendation,
)

router = APIRouter()


@router.post("", response_model=OptimizationResponse)
async def optimize_portfolio(request: OptimizationRequest) -> OptimizationResponse:
    """
    Run Merton portfolio optimization.

    Takes asset returns, volatilities, correlations, and CRRA parameter
    to calculate optimal portfolio weights.
    """
    try:
        optimizer = PortfolioOptimizer(
            asset_names=request.assets,
            expected_returns=request.expected_returns,
            volatilities=request.volatilities,
            correlation_matrix=request.correlation_matrix,
            crra=request.crra,
        )

        result = optimizer.optimize()

        # Map the result to response model
        stats = result["portfolio_stats"]
        return OptimizationResponse(
            optimal_weights=result["optimal_weights"],
            portfolio_stats=PortfolioStats(
                return_pct=stats["return"],
                volatility=stats["volatility"],
                sharpe_ratio=stats["sharpe_ratio"],
                crra_utility=stats["crra_utility"],
                risk_contribution=stats["risk_contribution"],
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/gap-analysis", response_model=GapAnalysisResponse)
async def calculate_gap_analysis(request: GapAnalysisRequest) -> GapAnalysisResponse:
    """
    Calculate gap analysis between current and target allocations.

    Priority rules (from step2 prompt):
    - High: Gap < -5% AND valuation favorable/neutral AND institutional not underweight
    - Medium: Gap -3% to -5% AND valuation favorable/neutral
    - Consider: Gap < -3% but valuation cautious OR institutional underweight
    - Hold: Gap within +/-3%
    - Skip: Gap > +3% (overweight)
    """
    rows = []
    high_priority = []
    medium_priority = []

    all_assets = set(request.current_allocation.keys()) | set(
        request.target_allocation.keys()
    )

    for asset in sorted(all_assets):
        current = request.current_allocation.get(asset, 0.0)
        target = request.target_allocation.get(asset, 0.0)
        gap = target - current

        # Get valuation and institutional stance if provided
        valuation = None
        institutional = None
        if request.valuations:
            valuation = request.valuations.get(asset)
        if request.institutional_stances:
            institutional = request.institutional_stances.get(asset)

        # Determine priority
        priority = _calculate_priority(gap, valuation, institutional)

        if priority == "high":
            high_priority.append(asset)
        elif priority == "medium":
            medium_priority.append(asset)

        rows.append(
            GapAnalysisRow(
                ticker=asset,
                current_pct=current,
                target_pct=target,
                gap=gap,
                priority=priority,
                valuation_signal=valuation,
                institutional_stance=institutional,
            )
        )

    return GapAnalysisResponse(
        rows=rows,
        high_priority=high_priority,
        medium_priority=medium_priority,
    )


def _calculate_priority(
    gap: float,
    valuation: str | None,
    institutional: str | None,
) -> str:
    """Calculate priority based on gap analysis rules."""
    # Skip if overweight
    if gap > 3:
        return "skip"

    # Hold if within +/-3%
    if -3 <= gap <= 3:
        return "hold"

    # Check for cautious signals
    is_cautious = valuation == "cautious" or institutional == "underweight"

    # High priority: Gap < -5% AND not cautious
    if gap < -5 and not is_cautious:
        return "high"

    # Medium priority: Gap -3% to -5% AND not cautious
    if -5 <= gap < -3 and not is_cautious:
        return "medium"

    # Consider: underweight but cautious signals
    if gap < -3 and is_cautious:
        return "consider"

    return "hold"


@router.post("/allocate", response_model=AllocationResponse)
async def calculate_allocation(request: AllocationRequest) -> AllocationResponse:
    """
    Calculate allocation recommendations for a contribution.

    Rules:
    - Only allocate to high or medium priority positions
    - Minimum allocation per ETF (default 500 EUR)
    - Concentrate in highest priorities if few qualify
    """
    recommendations = []
    remaining = request.contribution_amount

    # Get priority assets
    priority_assets = request.gap_analysis.high_priority + request.gap_analysis.medium_priority

    if not priority_assets:
        return AllocationResponse(
            total_contribution=request.contribution_amount,
            recommendations=[],
            unallocated=request.contribution_amount,
        )

    # Find gap data for priority assets
    priority_gaps = {}
    for row in request.gap_analysis.rows:
        if row.ticker in priority_assets:
            priority_gaps[row.ticker] = abs(row.gap)

    # Sort by gap size (largest first)
    sorted_assets = sorted(priority_gaps.keys(), key=lambda x: priority_gaps[x], reverse=True)

    # Calculate proportional allocation based on gap size
    total_gap = sum(priority_gaps.values())

    for asset in sorted_assets:
        if remaining < request.min_allocation:
            break

        # Calculate proportional amount
        proportion = priority_gaps[asset] / total_gap if total_gap > 0 else 1 / len(sorted_assets)
        amount = request.contribution_amount * proportion

        # Round to minimum allocation
        amount = max(request.min_allocation, round(amount / 100) * 100)
        amount = min(amount, remaining)

        if amount >= request.min_allocation:
            # Find the row for rationale
            row = next((r for r in request.gap_analysis.rows if r.ticker == asset), None)
            rationale = _build_rationale(row) if row else ""

            recommendations.append(
                AllocationRecommendation(
                    ticker=asset,
                    amount_eur=amount,
                    percentage_of_contribution=(amount / request.contribution_amount) * 100,
                    rationale=rationale,
                )
            )
            remaining -= amount

    return AllocationResponse(
        total_contribution=request.contribution_amount,
        recommendations=recommendations,
        unallocated=remaining,
    )


def _build_rationale(row: GapAnalysisRow) -> str:
    """Build rationale string for allocation recommendation."""
    parts = [f"{abs(row.gap):.1f}% underweight"]

    if row.valuation_signal:
        signal_emoji = {"favorable": "favorable", "neutral": "neutral", "cautious": "cautious"}
        parts.append(f"{signal_emoji.get(row.valuation_signal, row.valuation_signal)} valuation")

    if row.institutional_stance:
        parts.append(f"institutional {row.institutional_stance}")

    return ", ".join(parts)
