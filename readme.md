# Portfolio Optimization

Tools for portfolio optimization and risk analysis, featuring customizable asset allocation based on CRRA (Constant Relative Risk Aversion) preferences.

## Project Structure

```
portfolio_optimization/
├── merton_share.py        # Core portfolio optimization implementation
├── crra_survey.py         # Interactive CRRA estimation tool
├── prompts/
│   ├── generate_input_data     # Prompt for generating portfolio inputs
│   └── portfolio_candidates    # Prompt for finding complementary ETFs
```

## Features

- Merton's optimal portfolio calculation
- Interactive CRRA estimation
- Data-driven portfolio input generation
- ETF portfolio expansion recommendations
- Risk analysis

## Prerequisites

- Python 3.8+
- Required packages: numpy, pandas, matplotlib, seaborn

Install dependencies:
```bash
pip install numpy pandas matplotlib seaborn
```

## Usage Guide

### 1. Determine Your Risk Profile (Optional)

Run the CRRA estimation survey:
```bash
python crra_survey.py
```
This will:
- Guide you through risk preference questions
- Calculate your CRRA value
- Save results to `crra_results.json`

### 2. Generate Portfolio Inputs

Use the `generate_input_data` prompt with GPT with web search access to create portfolio inputs:

1. Copy the prompt from `prompts/generate_input_data`
2. Provide it to GPT
3. Save the output JSONs:
   - `portfolio_data.json`: Core optimization inputs
   - `metadata.json`: Calculation details and data quality

Example portfolio_data.json:
```json
{
  "assets": ["COI1228", "ETFSP500", "4GLD", "VZLC"],
  "returns": [0.0600, 0.1200, 0.0800, 0.0700],
  "volatilities": [0.0200, 0.1800, 0.2000, 0.2200],
  "correlations": [
    [1.0000, 0.2000, 0.1500, 0.1000],
    [0.2000, 1.0000, 0.3000, 0.2500],
    [0.1500, 0.3000, 1.0000, 0.5000],
    [0.1000, 0.2500, 0.5000, 1.0000]
  ],
  "crra": 2.9
}
```

### 3. Run Portfolio Optimization

```bash
python merton_share.py --config portfolio_data.json --output results.json
```

The optimizer will:
- Validate input data
- Calculate optimal weights
- Generate portfolio statistics
- Save detailed results to specified output file

### 4. Find Complementary ETFs (Optional)

Use the `portfolio_candidates` prompt to find additional ETFs:

1. Copy the prompt from `prompts/portfolio_candidates`
2. Provide it to GPT with your current portfolio
3. Review recommendations and verification data

## Theoretical Framework
The portfolio optimizer implements Merton's optimal portfolio selection model, which determines the optimal allocation between risky and risk-free assets based on an investor's risk aversion.
### Merton Share Equation
The core equation for optimal allocation is:
α* = (μ - r)/(γσ²)
where:

α* is the optimal fraction of wealth invested in risky assets
μ is the expected return of the risky asset
r is the risk-free rate
γ (gamma) is the coefficient of relative risk aversion (CRRA)
σ² is the variance of the risky asset

For multiple risky assets, the formula extends to:
α* = (1/γ) * Σ⁻¹(μ - r*1)
where:

Σ⁻¹ is the inverse of the variance-covariance matrix
μ - r*1 is the vector of excess returns
The resulting α* is a vector of optimal weights

## Input Data Requirements

### Portfolio Data
- Asset identifiers must be consistent
- Returns and volatilities in decimal form
- All values rounded to 4 decimal places
- Correlation matrix must be symmetric and positive definite
- All data in EUR base currency

### Validation Ranges

Returns (Annual):
- Bonds: [-0.02, 0.10]
- Equities: [-0.10, 0.25]
- Precious Metals: [-0.05, 0.20]

Volatilities (Annual):
- Bonds: [0.01, 0.05]
- Equities: [0.15, 0.25]
- Precious Metals: [0.15, 0.30]

## Advanced Usage

### Custom CRRA Values

Override the default CRRA in your input JSON:
```json
{
  "crra": 3.5,
  "assets": [...],
  ...
}
```

### Output Interpretation

The optimizer provides:
- Optimal asset weights
- Expected portfolio return
- Portfolio volatility
- Sharpe ratio
- CRRA utility
- Risk contributions per asset

Example output:
```json
{
  "weights": {
    "COI1228": 40.5,
    "ETFSP500": 25.3,
    "4GLD": 20.1,
    "VZLC": 14.1
  },
  "stats": {
    "return": 8.25,
    "volatility": 12.45,
    "sharpe_ratio": 0.543,
    "crra_utility": 0.234
  }
}
```