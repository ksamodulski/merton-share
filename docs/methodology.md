# Merton Share Methodology

This document explains the quantitative methodology used in the Merton Share portfolio optimizer.

## Overview

Merton Share implements mean-variance portfolio optimization using a CRRA (Constant Relative Risk Aversion) utility function. The optimizer takes expected returns, volatilities, and correlations as inputs and outputs optimal portfolio weights.

## Expected Returns Estimation

### Primary Method: Claude AI with Web Search

Claude AI gathers current market data using web search from authoritative sources:

| Data Point | Primary Sources |
|------------|-----------------|
| CAPE Ratios | multpl.com/shiller-pe, Shiller's Yale data |
| Volatility | VIX (CBOE), VSTOXX (stoxx.com) |
| ECB Rates | ecb.europa.eu |
| Dividend Yields | S&P Global, MSCI |
| Institutional Views | BlackRock, Vanguard, Goldman Sachs outlook reports |

Each data point includes:
- Source citation
- Date of data
- Confidence level (high/medium/low)

### Expected Returns Formula

For equities, expected returns are estimated using:

```
Expected Return = (1 / CAPE) + Dividend Yield + Growth Adjustment
```

Where:
- `1 / CAPE` = Cyclically-adjusted earnings yield
- `Dividend Yield` = Current dividend yield
- `Growth Adjustment` = Regional growth expectations (typically -1% to +2%)

### Fallback Method

If Claude's expected returns are unavailable, the frontend calculates:

```
Expected Return = (1 / CAPE) + Dividend Yield
```

With a hard default of 5% if no data is available.

### Validation Bounds

Expected returns are flagged as suspicious if outside the typical range:
- **Minimum**: -5% (severe recession/deflation scenario)
- **Maximum**: +15% (extremely optimistic)

Values outside this range trigger a user confirmation modal where you can:
- Confirm (proceed with the value)
- Reject (re-fetch data)
- Override (manually enter a value)

## Gold Policy

Gold is treated as a **diversifying real asset**, not a safe-haven bond.

### Expected Return Assumption

- Long-term real return: ~0% to +2%
- Nominal return: Inflation expectation + 0-2%
- Default: ~3-4% nominal (2% real + 2% inflation)

### Volatility

- Historical: ~15% annualized
- Lower than EM equities, similar to developed market equities

### Role in Portfolio

Gold's value comes from diversification (low correlation with equities), not expected return. The optimizer may allocate to Gold even with modest return expectations because of its correlation benefits.

## Risk-Free Rate

### Source

ECB deposit facility rate or German 10-year Bund yield (whichever is higher), appropriate for EUR-denominated portfolios.

### Default Value

2.5% (configurable in settings)

### Usage

The risk-free rate is used for:
1. Sharpe ratio calculation
2. Excess return calculations
3. Not directly in the CRRA optimization (which uses total returns)

## Correlation Matrix

### Default Values

| Asset  | US   | Europe | Japan | EM   | Gold |
|--------|------|--------|-------|------|------|
| US     | 1.00 | 0.85   | 0.65  | 0.70 | 0.05 |
| Europe | 0.85 | 1.00   | 0.60  | 0.65 | 0.10 |
| Japan  | 0.65 | 0.60   | 1.00  | 0.55 | 0.05 |
| EM     | 0.70 | 0.65   | 0.55  | 1.00 | 0.15 |
| Gold   | 0.05 | 0.10   | 0.05  | 0.15 | 1.00 |

### Source

Based on rolling 10-year historical correlations. Key characteristics:
- US-Europe: Highly correlated (0.85)
- Japan: Lower correlation with other markets (0.55-0.65)
- Gold: Near-zero correlation with equities (0.05-0.15)

## Merton Optimization

### Utility Function

CRRA (Constant Relative Risk Aversion):

```
U(W) = W^(1-γ) / (1-γ)  for γ ≠ 1
U(W) = ln(W)             for γ = 1
```

Where γ (gamma) is the CRRA coefficient.

### Quadratic Approximation

For computational efficiency, we use the quadratic approximation:

```
E[U] ≈ μ_p - (γ/2) × σ_p²
```

Where:
- μ_p = Portfolio expected return
- σ_p² = Portfolio variance
- γ = CRRA coefficient

### Optimization Objective

Maximize expected utility subject to constraints:

```
max E[U] = μ_p - (γ/2) × σ_p²
```

### Constraints

1. **Budget constraint**: Weights sum to 100%
2. **Long-only**: All weights ≥ 0%
3. **Diversification**: Each weight ≤ 50%

## View Blending (Optional)

### Black-Litterman Lite

When enabled (`use_views_in_optimization = True`), institutional views adjust expected returns:

| Stance | Return Adjustment |
|--------|-------------------|
| Overweight | +1.0% |
| Neutral | 0% |
| Underweight | -1.0% |

Additionally, valuation signals can add smaller adjustments:

| Signal | Return Adjustment |
|--------|-------------------|
| Favorable | +0.5% |
| Neutral | 0% |
| Cautious | -1.0% |

### Example

If Claude returns:
- US expected return: 5.0%
- Institutional view: Overweight

With view blending enabled:
- Adjusted US return: 5.0% + 1.0% = 6.0%

## Uncertainty Estimation

### Confidence Intervals

The optimizer provides a 95% confidence interval for portfolio expected return based on:
1. Spread of input expected returns (estimation error proxy)
2. Portfolio concentration (Herfindahl index)

### Uncertainty Categories

| Category | Return Spread | Interpretation |
|----------|---------------|----------------|
| Low | < 1.5% | Inputs are consistent |
| Medium | 1.5% - 3.0% | Some estimation uncertainty |
| High | > 3.0% | Significant input variation |

### Limitations

This is a simplified uncertainty estimate. More sophisticated approaches would use:
- Bootstrap resampling
- Analytical estimation error formulas
- Bayesian posterior distributions

## Bonds vs Risky Assets Split

### Heuristic Rule

For the split between Polish inflation-linked bonds and risky assets:

```
Target Risky % = 100 / γ
```

Where γ is the CRRA coefficient.

| CRRA | Target Risky | Target Bonds |
|------|--------------|--------------|
| 1.5 | 67% | 33% |
| 2.0 | 50% | 50% |
| 3.0 | 33% | 67% |
| 5.0 | 20% | 80% |

### Rationale

This approximation assumes a Sharpe ratio of ~1 for risky assets. It's a simplification because Polish bonds have different characteristics than a theoretical risk-free asset.

## Configuration

Key settings in `backend/app/config.py`:

```python
# Methodology settings
use_views_in_optimization: bool = False  # Enable BL-lite view blending
expected_return_min: float = -0.05       # -5% lower bound
expected_return_max: float = 0.15        # +15% upper bound
default_risk_free_rate: float = 0.025    # 2.5% default ECB rate

# View blending adjustments
institutional_view_adjustment: float = 0.01  # +/-1% per stance
valuation_signal_adjustment: float = 0.005   # +/-0.5% per signal
```

## References

1. Merton, R.C. (1969). "Lifetime Portfolio Selection under Uncertainty: The Continuous-Time Case"
2. Black, F. & Litterman, R. (1992). "Global Portfolio Optimization"
3. Campbell, J.Y. & Shiller, R.J. (1998). "Valuation Ratios and the Long-Run Stock Market Outlook"
