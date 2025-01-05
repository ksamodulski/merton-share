import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import json
import sys
from typing import Dict, List, Union

class PortfolioOptimizer:
    def __init__(self, 
                 asset_names: List[str],
                 expected_returns: List[float],
                 volatilities: List[float],
                 correlation_matrix: Union[List[List[float]], np.ndarray],
                 crra: float = 3):
        try:
            self.asset_names = asset_names
            self.expected_returns = np.array(expected_returns)
            self.volatilities = np.array(volatilities)
            self.correlation_matrix = np.array(correlation_matrix)
            
            if crra <= 0:
                raise ValueError("CRRA parameter must be positive")
            self.crra = crra
            
            self._validate_inputs()
            
            self.bond_index = np.argmin(volatilities)
            self.risk_free_rate = expected_returns[self.bond_index]
            
            self.risky_indices = [i for i in range(len(asset_names)) if i != self.bond_index]
            self.risky_returns = self.expected_returns[self.risky_indices]
            self.risky_vols = self.volatilities[self.risky_indices]
            self.risky_corr = self.correlation_matrix[np.ix_(self.risky_indices, self.risky_indices)]
            
            self.risky_cov = np.diag(self.risky_vols) @ \
                            self.risky_corr @ \
                            np.diag(self.risky_vols)
                            
        except Exception as e:
            raise ValueError(f"Error initializing optimizer: {str(e)}")

    def _validate_inputs(self):
        if not self.asset_names or len(self.asset_names) < 2:
            raise ValueError("At least two assets are required")
        if len(self.asset_names) != len(self.expected_returns):
            raise ValueError("Number of assets doesn't match number of returns")
        if len(self.asset_names) != len(self.volatilities):
            raise ValueError("Number of assets doesn't match number of volatilities")
        if self.correlation_matrix.shape != (len(self.asset_names), len(self.asset_names)):
            raise ValueError("Correlation matrix dimensions don't match number of assets")
        if not np.allclose(self.correlation_matrix, self.correlation_matrix.T):
            raise ValueError("Correlation matrix is not symmetric")
        if not np.allclose(np.diag(self.correlation_matrix), 1):
            raise ValueError("Correlation matrix diagonal elements are not 1")
        if np.any(self.volatilities <= 0):
            raise ValueError("Volatilities must be positive")
        if not np.all(np.linalg.eigvals(self.correlation_matrix) > 0):
            raise ValueError("Correlation matrix is not positive definite")

    def calculate_optimal_weights(self):
        try:
            # Calculate excess returns for risky assets
            excess_returns = self.risky_returns - self.risk_free_rate
            print("\nDebug Information:")
            print(f"Excess returns: {excess_returns}")
            
            # Calculate optimal weights for risky assets
            inv_cov = np.linalg.inv(self.risky_cov)
            print(f"Inverse covariance matrix:\n{inv_cov}")
            
            # Step 1: Calculate initial proportions between risky assets
            risky_proportions = inv_cov @ excess_returns
            print(f"Initial risky proportions (before constraints): {risky_proportions}")
            
            # Enforce non-negative constraints
            risky_proportions = np.maximum(risky_proportions, 0)
            print(f"Risky proportions (after non-negative constraint): {risky_proportions}")
            
            # Normalize if sum is positive
            sum_proportions = np.sum(risky_proportions)
            if sum_proportions > 0:
                normalized_risky_proportions = risky_proportions / sum_proportions
            else:
                normalized_risky_proportions = np.zeros_like(risky_proportions)
            print(f"Normalized risky proportions: {normalized_risky_proportions}")
            
            # Step 2: Calculate total allocation to risky assets based on CRRA
            scaling_factor = 1 / self.crra
            total_risky_allocation = min(1, scaling_factor)
            print(f"CRRA value: {self.crra}")
            print(f"Total risky allocation: {total_risky_allocation}")
            
            # Step 3: Create final weights array
            weights = np.zeros(len(self.asset_names))
            for i, idx in enumerate(self.risky_indices):
                weights[idx] = normalized_risky_proportions[i] * total_risky_allocation
            
            # Remainder goes to bonds
            weights[self.bond_index] = 1 - total_risky_allocation
            
            print(f"Final weights: {weights}")
            return weights
                
        except np.linalg.LinAlgError:
            raise ValueError("Error: Covariance matrix is singular. Check your inputs.")
        except Exception as e:
            raise ValueError(f"Error calculating weights: {str(e)}")

    def calculate_portfolio_stats(self, weights):
        try:
            portfolio_return = np.sum(weights * self.expected_returns)
            portfolio_vol = np.sqrt(
                weights.T @ np.diag(self.volatilities) @ 
                self.correlation_matrix @ 
                np.diag(self.volatilities) @ weights
            )
            
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
            
            if np.isclose(self.crra, 1.0):
                crra_utility = np.log(1 + portfolio_return) - \
                              (portfolio_vol * portfolio_vol / 2)
            else:
                crra_utility = (np.power(1 + portfolio_return, 1 - self.crra) / (1 - self.crra)) - \
                              (portfolio_vol * portfolio_vol / 2)
            
            return {
                'return': portfolio_return * 100,
                'volatility': portfolio_vol * 100,
                'sharpe_ratio': sharpe_ratio,
                'crra_utility': crra_utility,
                'risk_contribution': self._calculate_risk_contributions(weights, portfolio_vol)
            }
            
        except Exception as e:
            raise ValueError(f"Error calculating portfolio statistics: {str(e)}")

    def _calculate_risk_contributions(self, weights, portfolio_vol):
        cov_matrix = np.diag(self.volatilities) @ self.correlation_matrix @ np.diag(self.volatilities)
        marginal_risk = (cov_matrix @ weights) / portfolio_vol if portfolio_vol > 0 else np.zeros_like(weights)
        risk_contribution = weights * marginal_risk
        return dict(zip(self.asset_names, risk_contribution * 100))

    def optimize_portfolio(self):
        weights = self.calculate_optimal_weights()
        stats = self.calculate_portfolio_stats(weights)
        
        return {
            'optimal_weights': dict(zip(self.asset_names, weights * 100)),
            'portfolio_stats': stats
        }

def parse_arguments():
    parser = argparse.ArgumentParser(description='Portfolio Optimization Calculator')
    parser.add_argument('--config', type=str, help='Path to JSON config file')
    parser.add_argument('--output', type=str, help='Output file path for results (optional)')
    return parser.parse_args()

def validate_config(config):
    required_fields = ['assets', 'returns', 'volatilities', 'correlations']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field in config: {field}")
    
    if not isinstance(config['assets'], list):
        raise ValueError("Assets must be a list")
    if not isinstance(config['returns'], list):
        raise ValueError("Returns must be a list")
    if not isinstance(config['volatilities'], list):
        raise ValueError("Volatilities must be a list")
    if not isinstance(config['correlations'], list):
        raise ValueError("Correlations must be a list")
    
    n_assets = len(config['assets'])
    if len(config['returns']) != n_assets:
        raise ValueError("Number of returns must match number of assets")
    if len(config['volatilities']) != n_assets:
        raise ValueError("Number of volatilities must match number of assets")
    if len(config['correlations']) != n_assets or any(len(row) != n_assets for row in config['correlations']):
        raise ValueError("Correlation matrix dimensions must match number of assets")

def main():
    try:
        args = parse_arguments()
        
        if not args.config:
            raise ValueError("Config file path is required")
        
        with open(args.config, 'r') as f:
            config = json.load(f)
        
        validate_config(config)
        
        optimizer = PortfolioOptimizer(
            asset_names=config['assets'],
            expected_returns=config['returns'],
            volatilities=config['volatilities'],
            correlation_matrix=config['correlations'],
            crra=config.get('crra', 3)
        )
        
        results = optimizer.optimize_portfolio()
        
        print("\nOptimal Portfolio Allocation:")
        print("----------------------------")
        for asset, weight in results['optimal_weights'].items():
            print(f"{asset}: {weight:.2f}%")
        
        print("\nPortfolio Statistics:")
        print("----------------------------")
        stats = results['portfolio_stats']
        print(f"Expected Return: {stats['return']:.2f}%")
        print(f"Portfolio Risk: {stats['volatility']:.2f}%")
        print(f"Sharpe Ratio: {stats['sharpe_ratio']:.3f}")
        print(f"CRRA Utility: {stats['crra_utility']:.3f}")
        
        print("\nRisk Contributions:")
        print("----------------------------")
        for asset, contrib in stats['risk_contribution'].items():
            print(f"{asset}: {contrib:.2f}%")
        
        if args.output:
            output_data = {
                'weights': results['optimal_weights'],
                'stats': results['portfolio_stats']
            }
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nResults saved to {args.output}")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()