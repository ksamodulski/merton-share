"""
Portfolio Optimizer using Merton's optimal portfolio allocation.

This module implements mean-variance optimization with CRRA (Constant Relative
Risk Aversion) utility function. All assets are treated as risky assets.
"""

import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Union


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

        Raises:
            ValueError: If inputs are invalid or inconsistent
        """
        self.asset_names = asset_names
        self.expected_returns = np.array(expected_returns)
        self.volatilities = np.array(volatilities)
        self.correlation_matrix = np.array(correlation_matrix)
        self.risk_free_rate = risk_free_rate

        if crra <= 0:
            raise ValueError("CRRA parameter must be positive")
        self.crra = crra

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

        # Initial guess: equal weights
        x0 = np.ones(n) / n

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},  # Weights sum to 1
        ]

        # Bounds: 0% to 50% for each asset (prevents extreme concentration)
        bounds = [(0.0, 0.50) for _ in range(n)]

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
            # Fall back to equal weights if optimization fails
            return np.ones(n) / n

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
            Dictionary with return, volatility, sharpe_ratio, crra_utility, risk_contribution
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

        return {
            "return": portfolio_return * 100,  # As percentage
            "volatility": portfolio_vol * 100,  # As percentage
            "sharpe_ratio": float(sharpe_ratio),
            "crra_utility": float(crra_utility),
            "risk_contribution": self._calculate_risk_contributions(
                weights, portfolio_vol
            ),
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
        }
