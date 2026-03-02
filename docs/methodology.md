# Merton Share Methodology

This document explains the quantitative methodology used in the Merton Share portfolio optimizer.

## Overview

Merton Share implements mean-variance portfolio optimization using a CRRA (Constant Relative Risk Aversion) utility function. The optimizer takes expected returns, volatilities, and correlations as inputs and outputs optimal portfolio weights.

## Expected Returns Estimation

### Primary Method: Live yfinance + Claude Web Search

Market data is gathered in two layers:

**Layer 1 — Live numbers via yfinance** (fetched at request time):

| Data Point | Source |
|------------|--------|
| VIX | `^VIX` via yfinance |
| VSTOXX | `^V2TX` via yfinance |
| Realized volatilities | SPY, VGK, EWJ, EEM, GLD 1-year daily returns |
| Trailing P/E ratios | yfinance `info.trailingPE` |
| EUR/PLN rate | `EURPLN=X` via yfinance |

**Layer 2 — Qualitative data via Claude web search**:

| Data Point | Primary Sources |
|------------|-----------------|
| CAPE Ratios | multpl.com/shiller-pe, Shiller's Yale data |
| ECB Rates | ecb.europa.eu |
| German Bund yield | web search |
| Dividend Yields | S&P Global, MSCI |
| Institutional Views | BlackRock, Vanguard, Goldman Sachs outlook reports |
| Breaking news | Web search for current geopolitical/macro events |

Each data point includes a `confidence` field:
- `"high"` — directly web-searched, current data
- `"medium"` — derived from real data (e.g., CAPE estimated from trailing P/E)
- `"low"` — pure Claude estimate

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

## View Blending

### Black-Litterman Lite

Institutional views from web-searched sources are applied as confidence-scaled adjustments to CAPE-based expected returns. The adjustment magnitude depends on how reliable the view is:

| Confidence | Source type | Scale | Overweight | Underweight |
|------------|-------------|-------|------------|-------------|
| `high` | Web-searched breaking news | ×1.0 | +2.0% | −2.0% |
| `medium` | Recent institutional reports / derived | ×0.75 | +1.5% | −1.5% |
| `low` | Pure Claude estimate | ×0.5 | +1.0% | −1.0% |
| (none) | Treated as low | ×0.5 | +1.0% | −1.0% |

The `confidence` field is set by Claude in the market data prompt: `"high"` for web-searched values, `"medium"` for estimates from real data, `"low"` for pure estimates.

Valuation signals can add smaller additional adjustments:

| Signal | Return Adjustment |
|--------|-------------------|
| Favorable | +0.5% |
| Neutral | 0% |
| Cautious | −1.0% |

### Example

If Claude returns:
- US expected return: 5.0% (CAPE-based)
- Institutional view: Overweight, confidence: **high** (web-searched)

Adjusted US return: 5.0% + (2.0% × 1.0) = **7.0%**

If the same view had confidence: **low** (estimate):

Adjusted US return: 5.0% + (2.0% × 0.5) = **6.0%**

### Why Confidence Matters

VIX is already the most direct channel for breaking news — a crisis spikes VIX and the CRRA optimizer automatically cuts equity weights. The institutional view adjustment is a secondary overlay. Scaling it by confidence ensures:
- A Claude training-data guess gets the same weight as before (±1%)
- A web-searched breaking-news stance gets double the influence (±2%)
- The confidence field is never ignored

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
expected_return_min: float = -0.05       # -5% lower bound
expected_return_max: float = 0.15        # +15% upper bound
default_risk_free_rate: float = 0.025    # 2.5% default ECB rate
```

View adjustment magnitudes are defined in `backend/app/core/view_mapping.py`:

```python
CONFIDENCE_SCALE = {"high": 1.0, "medium": 0.75, "low": 0.5, None: 0.5}
BASE_VIEW_ADJUSTMENT = {"overweight": +0.02, "neutral": 0.0, "underweight": -0.02}
# Effective range: ±1% (low/None) to ±2% (high)
```

## References

1. Merton, R.C. (1969). "Lifetime Portfolio Selection under Uncertainty: The Continuous-Time Case"
2. Black, F. & Litterman, R. (1992). "Global Portfolio Optimization"
3. Campbell, J.Y. & Shiller, R.J. (1998). "Valuation Ratios and the Long-Run Stock Market Outlook"
