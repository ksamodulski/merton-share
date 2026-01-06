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
    PostAllocationPosition,
    RebalanceCheckRequest,
    RebalanceResponse,
    SellRecommendation,
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
    """
    Calculate priority based on gap analysis rules.

    Gap = target - current:
    - Positive gap: underweight (need to BUY)
    - Negative gap: overweight (should SKIP buying, maybe SELL)
    """
    # Skip if overweight (current > target)
    if gap < -3:
        return "skip"

    # Hold if within +/-3%
    if -3 <= gap <= 3:
        return "hold"

    # Check for cautious signals (reasons to NOT buy)
    is_cautious = valuation == "cautious" or institutional == "underweight"

    # High priority: Gap > 5% (significantly underweight) AND not cautious
    if gap > 5 and not is_cautious:
        return "high"

    # Medium priority: Gap 3% to 5% (moderately underweight) AND not cautious
    if 3 < gap <= 5 and not is_cautious:
        return "medium"

    # Consider: underweight but cautious signals suggest caution
    if gap > 3 and is_cautious:
        return "consider"

    return "hold"


@router.post("/allocate", response_model=AllocationResponse)
async def calculate_allocation(request: AllocationRequest) -> AllocationResponse:
    """
    Calculate allocation recommendations for a contribution.

    Logic:
    1. Calculate future portfolio value (current + contribution)
    2. For each underweight asset, calculate EUR needed to reach target
    3. Spread contribution across underweight assets proportionally
    4. Respect minimum allocation per ETF
    """
    recommendations = []
    contribution = request.contribution_amount
    current_value = request.current_portfolio_value
    future_value = current_value + contribution

    # Calculate EUR gap for each asset based on FUTURE position after contribution
    # Key insight: An asset that's overweight NOW may become underweight AFTER
    # the contribution dilutes its percentage (if no money is added to it)
    #
    # Example: EM at 28.8% of €17k = €4,896
    #          After €20k contribution: €4,896 / €37k = 13.2%
    #          If target is 24%, EM is now UNDERWEIGHT and needs money
    eur_gaps = {}
    for row in request.gap_analysis.rows:
        current_eur = (row.current_pct / 100) * current_value
        # What % will this be if we add nothing to it?
        future_pct_if_no_addition = (current_eur / future_value) * 100

        # Will this asset be underweight after contribution (if we add nothing)?
        if future_pct_if_no_addition < row.target_pct:
            target_eur = (row.target_pct / 100) * future_value
            eur_needed = target_eur - current_eur
            if eur_needed > 0:
                eur_gaps[row.ticker] = eur_needed

    if not eur_gaps:
        return AllocationResponse(
            total_contribution=contribution,
            recommendations=[],
            unallocated=contribution,
        )

    # Calculate total EUR needed to fill all gaps
    total_eur_needed = sum(eur_gaps.values())

    # Sort assets by EUR gap (largest first)
    sorted_gaps = sorted(eur_gaps.items(), key=lambda x: x[1], reverse=True)

    # Allocate based on EUR gaps
    remaining = contribution
    allocations = {}

    # First pass: calculate ideal proportional allocations
    ideal_allocations = {}
    for asset, eur_needed in sorted_gaps:
        if total_eur_needed <= contribution:
            ideal_allocations[asset] = eur_needed
        else:
            proportion = eur_needed / total_eur_needed
            ideal_allocations[asset] = contribution * proportion

    # Second pass: consolidate small allocations into larger ones
    # If individual allocation < min_allocation, concentrate into fewer assets
    viable_assets = [a for a, amt in ideal_allocations.items() if amt >= request.min_allocation]

    if not viable_assets and sorted_gaps:
        # No single allocation meets minimum - concentrate into top N assets
        # that can each receive at least min_allocation
        max_assets = int(contribution / request.min_allocation)
        if max_assets > 0:
            viable_assets = [a for a, _ in sorted_gaps[:max_assets]]

    # Recalculate for viable assets only
    if viable_assets:
        viable_eur_gaps = {a: eur_gaps[a] for a in viable_assets}
        viable_total = sum(viable_eur_gaps.values())

        for asset in viable_assets:
            if remaining < request.min_allocation:
                break

            if viable_total <= remaining:
                amount = viable_eur_gaps[asset]
            else:
                proportion = viable_eur_gaps[asset] / viable_total
                amount = contribution * proportion

            # Round to nearest 100
            amount = round(amount / 100) * 100
            amount = max(request.min_allocation, amount)  # Ensure minimum
            amount = min(amount, remaining)  # Cap at remaining

            if amount >= request.min_allocation:
                allocations[asset] = amount
                remaining -= amount

    # If we have extra (all gaps filled with money left over), distribute proportionally
    if remaining >= request.min_allocation and allocations:
        extra_per_asset = remaining / len(allocations)
        for asset in allocations:
            extra = round(extra_per_asset / 100) * 100
            if extra >= 100:
                allocations[asset] += extra
                remaining -= extra

    # Build recommendations
    for asset, amount in allocations.items():
        row = next((r for r in request.gap_analysis.rows if r.ticker == asset), None)
        eur_needed = eur_gaps.get(asset, 0)

        # Build rationale showing how this moves toward target
        if row:
            new_value = (row.current_pct / 100) * current_value + amount
            new_pct = (new_value / future_value) * 100
            rationale = f"{row.gap:.1f}% underweight → {new_pct:.1f}% after (target: {row.target_pct:.1f}%)"
        else:
            rationale = f"€{eur_needed:,.0f} needed to reach target"

        recommendations.append(
            AllocationRecommendation(
                ticker=asset,
                amount_eur=amount,
                percentage_of_contribution=(amount / contribution) * 100,
                rationale=rationale,
            )
        )

    # Sort by amount (largest first)
    recommendations.sort(key=lambda r: r.amount_eur, reverse=True)

    # Build post-allocation preview for ALL positions
    preview = []
    for row in request.gap_analysis.rows:
        current_eur = (row.current_pct / 100) * current_value
        amount_added = allocations.get(row.ticker, 0)
        new_eur = current_eur + amount_added
        new_pct = (new_eur / future_value) * 100 if future_value > 0 else 0

        preview.append(
            PostAllocationPosition(
                ticker=row.ticker,
                current_eur=round(current_eur, 2),
                current_pct=row.current_pct,
                amount_added=amount_added,
                new_eur=round(new_eur, 2),
                new_pct=round(new_pct, 2),
                pct_change=round(new_pct - row.current_pct, 2),
                target_pct=row.target_pct,
                gap_after=round(row.target_pct - new_pct, 2),
            )
        )

    # Sort preview by gap_after (most underweight first)
    preview.sort(key=lambda p: p.gap_after, reverse=True)

    return AllocationResponse(
        total_contribution=contribution,
        recommendations=recommendations,
        unallocated=remaining,
        post_allocation_preview=preview,
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


@router.post("/rebalance-check", response_model=RebalanceResponse)
async def check_rebalancing(request: RebalanceCheckRequest) -> RebalanceResponse:
    """
    Check if portfolio rebalancing is recommended.

    Analyzes deviation from target allocation and identifies
    positions that are significantly overweight (candidates for selling).
    """
    overweight_positions = []
    underweight_positions = []
    max_deviation = 0.0

    all_assets = set(request.current_allocation.keys()) | set(
        request.target_allocation.keys()
    )

    for asset in sorted(all_assets):
        current = request.current_allocation.get(asset, 0.0)
        target = request.target_allocation.get(asset, 0.0)
        gap = target - current  # Positive = underweight, Negative = overweight
        deviation = abs(gap)

        max_deviation = max(max_deviation, deviation)

        # Significantly overweight (negative gap exceeds threshold)
        if gap < -request.rebalance_threshold:
            excess = abs(gap)
            overweight_positions.append(
                SellRecommendation(
                    ticker=asset,
                    current_pct=current,
                    target_pct=target,
                    excess_pct=excess,
                    rationale=f"Position is {excess:.1f}% above target allocation"
                )
            )
        # Significantly underweight (positive gap exceeds threshold)
        elif gap > request.rebalance_threshold:
            underweight_positions.append(asset)

    # Recommend rebalancing if any position exceeds threshold
    is_rebalance_recommended = len(overweight_positions) > 0 or len(underweight_positions) > 0

    return RebalanceResponse(
        is_rebalance_recommended=is_rebalance_recommended,
        max_deviation=max_deviation,
        overweight_positions=overweight_positions,
        underweight_positions=underweight_positions,
    )
