"""
Portfolio Optimizer using Merton's optimal portfolio allocation.

This module implements the Merton model for portfolio optimization with
CRRA (Constant Relative Risk Aversion) utility function.
"""

import numpy as np
from typing import Dict, List, Union


class PortfolioOptimizer:
    """
    Optimizes portfolio allocation using Merton's optimal portfolio theory.

    The optimizer identifies the lowest-volatility asset as the "bond" (risk-free asset)
    and calculates optimal weights for risky assets based on the CRRA parameter.
    """

    def __init__(
        self,
        asset_names: List[str],
        expected_returns: List[float],
        volatilities: List[float],
        correlation_matrix: Union[List[List[float]], np.ndarray],
        crra: float = 3.0,
    ):
        """
        Initialize the portfolio optimizer.

        Args:
            asset_names: List of asset identifiers (e.g., tickers)
            expected_returns: Expected annual returns for each asset (as decimals)
            volatilities: Annual volatility (std dev) for each asset (as decimals)
            correlation_matrix: Correlation matrix between assets
            crra: Coefficient of Relative Risk Aversion (1-10 typical range)

        Raises:
            ValueError: If inputs are invalid or inconsistent
        """
        self.asset_names = asset_names
        self.expected_returns = np.array(expected_returns)
        self.volatilities = np.array(volatilities)
        self.correlation_matrix = np.array(correlation_matrix)

        if crra <= 0:
            raise ValueError("CRRA parameter must be positive")
        self.crra = crra

        self._validate_inputs()

        # Identify bond as lowest volatility asset
        self.bond_index = int(np.argmin(volatilities))
        self.risk_free_rate = expected_returns[self.bond_index]

        # Separate risky assets
        self.risky_indices = [i for i in range(len(asset_names)) if i != self.bond_index]
        self.risky_returns = self.expected_returns[self.risky_indices]
        self.risky_vols = self.volatilities[self.risky_indices]
        self.risky_corr = self.correlation_matrix[
            np.ix_(self.risky_indices, self.risky_indices)
        ]

        # Calculate covariance matrix for risky assets
        self.risky_cov = (
            np.diag(self.risky_vols) @ self.risky_corr @ np.diag(self.risky_vols)
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

    def calculate_optimal_weights(self) -> np.ndarray:
        """
        Calculate optimal portfolio weights using Merton's formula.

        Returns:
            Array of optimal weights for each asset (sums to 1.0)
        """
        # Calculate excess returns for risky assets
        excess_returns = self.risky_returns - self.risk_free_rate

        # Calculate optimal weights for risky assets
        inv_cov = np.linalg.inv(self.risky_cov)

        # Step 1: Calculate initial proportions between risky assets
        risky_proportions = inv_cov @ excess_returns

        # Enforce non-negative constraints
        risky_proportions = np.maximum(risky_proportions, 0)

        # Normalize if sum is positive
        sum_proportions = np.sum(risky_proportions)
        if sum_proportions > 0:
            normalized_risky_proportions = risky_proportions / sum_proportions
        else:
            normalized_risky_proportions = np.zeros_like(risky_proportions)

        # Step 2: Calculate total allocation to risky assets based on CRRA
        scaling_factor = 1 / self.crra
        total_risky_allocation = min(1, scaling_factor)

        # Step 3: Create final weights array
        weights = np.zeros(len(self.asset_names))
        for i, idx in enumerate(self.risky_indices):
            weights[idx] = normalized_risky_proportions[i] * total_risky_allocation

        # Remainder goes to bonds
        weights[self.bond_index] = 1 - total_risky_allocation

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
        portfolio_vol = float(
            np.sqrt(
                weights.T
                @ np.diag(self.volatilities)
                @ self.correlation_matrix
                @ np.diag(self.volatilities)
                @ weights
            )
        )

        sharpe_ratio = (
            (portfolio_return - self.risk_free_rate) / portfolio_vol
            if portfolio_vol > 0
            else 0
        )

        if np.isclose(self.crra, 1.0):
            crra_utility = np.log(1 + portfolio_return) - (
                portfolio_vol * portfolio_vol / 2
            )
        else:
            crra_utility = (
                np.power(1 + portfolio_return, 1 - self.crra) / (1 - self.crra)
            ) - (portfolio_vol * portfolio_vol / 2)

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
        cov_matrix = (
            np.diag(self.volatilities)
            @ self.correlation_matrix
            @ np.diag(self.volatilities)
        )
        marginal_risk = (
            (cov_matrix @ weights) / portfolio_vol
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
