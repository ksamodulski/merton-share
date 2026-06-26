"""
Portfolio Optimizer using Merton's optimal portfolio allocation.

This module implements mean-variance optimization with CRRA (Constant Relative
Risk Aversion) utility function. All assets are treated as risky assets.
"""

import logging
import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# Approximate share of global equity market cap by region (~2026, float-adjusted).
# Used to derive per-region weight caps so a small region cannot dominate the
# long-only optimum (mean-variance has no notion of capacity or market cap).
GLOBAL_MARKET_CAP_WEIGHTS: Dict[str, float] = {
    "US": 0.62,
    "Europe": 0.15,
    "Japan": 0.06,
    "EM": 0.10,
    "Pacific": 0.03,  # developed Asia-Pacific ex-Japan (AUS/HK/SG/NZ)
}

# Gold is a diversifier/hedge, not an equity market cap — give it a fixed cap
# rather than deriving one from a market weight.
GOLD_MAX_WEIGHT = 0.25


def default_max_weights(
    asset_names: List[str],
    multiplier: float = 4.0,
    ceiling: float = 0.50,
    floor: float = 0.10,
) -> List[float]:
    """
    Build per-asset upper bounds from global market-cap weights.

    For each region: cap = clamp(market_weight * multiplier, floor, ceiling).
    Gold gets a fixed cap; unknown asset names (e.g. raw tickers) fall back to
    the ceiling so non-region uses are unaffected.

    If the resulting caps cannot sum to 1.0 (e.g. a basket of only small
    regions), they are relaxed to the flat ceiling so the sum-to-one constraint
    stays feasible.
    """
    caps: List[float] = []
    for name in asset_names:
        if name == "Gold":
            caps.append(GOLD_MAX_WEIGHT)
        elif name in GLOBAL_MARKET_CAP_WEIGHTS:
            raw = GLOBAL_MARKET_CAP_WEIGHTS[name] * multiplier
            caps.append(min(ceiling, max(floor, raw)))
        else:
            caps.append(ceiling)

    # Feasibility guard: weights must be able to sum to 1.0.
    if sum(caps) < 1.0:
        caps = [ceiling] * len(asset_names)

    return caps


def shrink_expected_returns(returns: np.ndarray, phi: float = 0.5) -> np.ndarray:
    """
    Apply Bayes-Stein (James-Stein) shrinkage toward the cross-sectional grand mean.

    Jorion (1986): the sample mean is inadmissible for N > 2 assets. Shrinking
    toward the equal-weight grand mean reduces estimation error by ~30-50%.

    Args:
        returns: Raw expected return estimates (as decimals)
        phi: Shrinkage intensity [0, 1]. 0 = no shrinkage, 1 = all assets get
             the grand mean. Default 0.5 per Jorion (1986) simulation results.

    Returns:
        Shrunk expected returns: (1 - phi) * returns + phi * grand_mean
    """
    grand_mean = float(np.mean(returns))
    shrunk = (1.0 - phi) * returns + phi * grand_mean
    return shrunk


class PortfolioOptimizer:
    """
    Optimizes portfolio allocation using mean-variance optimization with CRRA utility.

    All provided assets are treated as risky assets. The optimizer finds weights
    that maximize CRRA utility: E[U(W)] where U(W) = W^(1-γ)/(1-γ) for γ ≠ 1.
    """

    def __init__(
        self,
        asset_names: List[str],
        expected_returns: List[float],
        volatilities: List[float],
        correlation_matrix: Union[List[List[float]], np.ndarray],
        crra: float = 3.0,
        risk_free_rate: float = 0.025,
        max_weights: Optional[List[float]] = None,
    ):
        """
        Initialize the portfolio optimizer.

        Args:
            asset_names: List of asset identifiers (e.g., tickers)
            expected_returns: Expected annual returns for each asset (as decimals)
            volatilities: Annual volatility (std dev) for each asset (as decimals)
            correlation_matrix: Correlation matrix between assets
            crra: Coefficient of Relative Risk Aversion (1-10 typical range)
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
            max_weights: Optional per-asset upper bounds (aligned to asset_names).
                Defaults to market-cap-derived caps so a small region can't
                dominate (see default_max_weights).

        Raises:
            ValueError: If inputs are invalid or inconsistent
        """
        self.asset_names = asset_names
        raw_returns = np.array(expected_returns)
        self.volatilities = np.array(volatilities)
        self.correlation_matrix = np.array(correlation_matrix)
        self.risk_free_rate = risk_free_rate

        if crra <= 0:
            raise ValueError("CRRA parameter must be positive")
        self.crra = crra

        # Per-asset upper bounds. Default to market-cap-derived caps.
        from app.config import get_settings
        _settings = get_settings()
        if max_weights is None:
            max_weights = default_max_weights(
                asset_names,
                multiplier=_settings.region_overweight_multiplier,
                ceiling=_settings.max_region_weight,
                floor=_settings.min_region_weight_cap,
            )
        if len(max_weights) != len(asset_names):
            raise ValueError("max_weights length must match number of assets")
        self.max_weights = list(max_weights)

        # Apply Bayes-Stein shrinkage (Jorion 1986) toward grand mean
        from app.config import get_settings
        phi = get_settings().shrinkage_intensity
        self.expected_returns = shrink_expected_returns(raw_returns, phi=phi)
        logger.debug(
            "Expected returns — raw: %s | shrunk (phi=%.2f): %s",
            [f"{r:.3f}" for r in raw_returns],
            phi,
            [f"{r:.3f}" for r in self.expected_returns],
        )

        self._validate_inputs()

        # Calculate covariance matrix
        self.cov_matrix = (
            np.diag(self.volatilities)
            @ self.correlation_matrix
            @ np.diag(self.volatilities)
        )

    def _validate_inputs(self) -> None:
        """Validate all inputs for consistency and correctness."""
        n = len(self.asset_names)

        if n < 2:
            raise ValueError("At least two assets are required")
        if len(self.expected_returns) != n:
            raise ValueError("Number of returns doesn't match number of assets")
        if len(self.volatilities) != n:
            raise ValueError("Number of volatilities doesn't match number of assets")
        if self.correlation_matrix.shape != (n, n):
            raise ValueError(
                "Correlation matrix dimensions don't match number of assets"
            )
        if not np.allclose(self.correlation_matrix, self.correlation_matrix.T):
            raise ValueError("Correlation matrix is not symmetric")
        if not np.allclose(np.diag(self.correlation_matrix), 1):
            raise ValueError("Correlation matrix diagonal elements must be 1")
        if np.any(self.volatilities <= 0):
            raise ValueError("Volatilities must be positive")
        if not np.all(np.linalg.eigvals(self.correlation_matrix) > 0):
            raise ValueError("Correlation matrix is not positive definite")

    def _crra_utility(self, weights: np.ndarray) -> float:
        """
        Calculate negative CRRA utility for optimization (minimize negative = maximize).

        For CRRA utility: U(W) = W^(1-γ)/(1-γ) for γ ≠ 1, ln(W) for γ = 1

        We use a quadratic approximation: E[U] ≈ μ - (γ/2)σ² where
        μ is portfolio return and σ is portfolio volatility.
        """
        portfolio_return = np.sum(weights * self.expected_returns)
        portfolio_var = weights.T @ self.cov_matrix @ weights

        # CRRA utility approximation: penalize variance based on risk aversion
        utility = portfolio_return - (self.crra / 2) * portfolio_var

        return -utility  # Negative because we minimize

    def calculate_optimal_weights(self) -> np.ndarray:
        """
        Calculate optimal portfolio weights using constrained optimization.

        Maximizes CRRA utility subject to:
        - Weights sum to 1
        - All weights >= 0 (long only)
        - Each weight <= 0.50 (max 50% in any single asset for diversification)

        Returns:
            Array of optimal weights for each asset (sums to 1.0)
        """
        n = len(self.asset_names)

        # Bounds: 0% to the per-asset cap (market-cap-derived, prevents a small
        # region from dominating the long-only optimum).
        bounds = [(0.0, self.max_weights[i]) for i in range(n)]

        # Initial guess: equal weights, clipped to the caps and renormalized so
        # the starting point is feasible w.r.t. the upper bounds.
        x0 = np.minimum(np.ones(n) / n, self.max_weights)
        x0 = x0 / np.sum(x0)

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},  # Weights sum to 1
        ]

        # Optimize
        result = minimize(
            self._crra_utility,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-9},
        )

        if not result.success:
            # Fall back to the feasible (cap-respecting) equal-weight start.
            return x0

        weights = result.x
        # Ensure weights are non-negative and sum to 1
        weights = np.maximum(weights, 0)
        weights = weights / np.sum(weights)

        return weights

    def calculate_portfolio_stats(self, weights: np.ndarray) -> Dict:
        """
        Calculate portfolio statistics for given weights.

        Args:
            weights: Portfolio weights array

        Returns:
            Dictionary with return, volatility, sharpe_ratio, crra_utility, risk_contribution,
            and uncertainty estimates (confidence interval, estimation_uncertainty)
        """
        portfolio_return = float(np.sum(weights * self.expected_returns))
        portfolio_var = float(weights.T @ self.cov_matrix @ weights)
        portfolio_vol = float(np.sqrt(portfolio_var))

        sharpe_ratio = (
            (portfolio_return - self.risk_free_rate) / portfolio_vol
            if portfolio_vol > 0
            else 0
        )

        # CRRA utility approximation
        crra_utility = portfolio_return - (self.crra / 2) * portfolio_var

        # Calculate uncertainty estimates
        uncertainty = self._estimate_uncertainty(weights, portfolio_return)

        return {
            "return": portfolio_return * 100,  # As percentage
            "volatility": portfolio_vol * 100,  # As percentage
            "sharpe_ratio": float(sharpe_ratio),
            "crra_utility": float(crra_utility),
            "risk_contribution": self._calculate_risk_contributions(
                weights, portfolio_vol
            ),
            "return_confidence_interval": uncertainty["return_confidence_interval"],
            "estimation_uncertainty": uncertainty["estimation_uncertainty"],
        }

    def _estimate_uncertainty(
        self, weights: np.ndarray, portfolio_return: float
    ) -> Dict:
        """
        Estimate uncertainty in portfolio statistics.

        This provides a simple uncertainty estimate based on the spread of
        input expected returns. More sophisticated approaches would use
        bootstrap resampling or analytical formulas from estimation theory.

        Args:
            weights: Portfolio weights array
            portfolio_return: Calculated portfolio return

        Returns:
            Dictionary with return_confidence_interval (95% CI) and
            estimation_uncertainty (low/medium/high)
        """
        # Use the standard deviation of expected returns as a proxy for estimation error
        return_spread = float(np.std(self.expected_returns))

        # Simple 95% confidence interval using 2 standard errors
        # This is a simplified approach - in practice, you'd use more
        # sophisticated estimation error propagation
        standard_error = return_spread / np.sqrt(len(self.expected_returns))

        ci_low = (portfolio_return - 2 * standard_error) * 100
        ci_high = (portfolio_return + 2 * standard_error) * 100

        # Also factor in portfolio weights - concentrated portfolios have more uncertainty
        weight_concentration = float(np.sum(weights ** 2))  # Herfindahl index
        concentration_adjustment = weight_concentration * return_spread * 100

        # Adjust CI for concentration
        ci_low -= concentration_adjustment
        ci_high += concentration_adjustment

        # Categorize overall uncertainty
        if return_spread < 0.015:
            estimation_uncertainty = "low"
        elif return_spread < 0.03:
            estimation_uncertainty = "medium"
        else:
            estimation_uncertainty = "high"

        return {
            "return_confidence_interval": (round(ci_low, 2), round(ci_high, 2)),
            "estimation_uncertainty": estimation_uncertainty,
        }

    def _calculate_risk_contributions(
        self, weights: np.ndarray, portfolio_vol: float
    ) -> Dict[str, float]:
        """Calculate risk contribution of each asset."""
        marginal_risk = (
            (self.cov_matrix @ weights) / portfolio_vol
            if portfolio_vol > 0
            else np.zeros_like(weights)
        )
        risk_contribution = weights * marginal_risk
        return {
            name: float(contrib * 100)
            for name, contrib in zip(self.asset_names, risk_contribution)
        }

    def optimize(self) -> Dict:
        """
        Run full optimization and return results.

        Returns:
            Dictionary with optimal_weights and portfolio_stats
        """
        weights = self.calculate_optimal_weights()
        stats = self.calculate_portfolio_stats(weights)

        return {
            "optimal_weights": {
                name: float(weight * 100)
                for name, weight in zip(self.asset_names, weights)
            },
            "portfolio_stats": stats,
            "shrunk_expected_returns": {
                name: float(ret)
                for name, ret in zip(self.asset_names, self.expected_returns)
            },
            "weight_caps": {
                name: float(cap)
                for name, cap in zip(self.asset_names, self.max_weights)
            },
        }
