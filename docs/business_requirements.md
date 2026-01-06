# Business Requirements

## Overview

Merton Share is a portfolio optimization tool for European retail investors who want to determine the optimal allocation between risky assets (ETFs) and safe assets (inflation-linked bonds) based on their personal risk tolerance.

## Target User

- European retail investor
- Uses Interactive Brokers (IBKR) as their broker
- Holds UCITS-compliant, EUR-denominated, accumulating ETFs
- May hold Polish inflation-linked bonds (obligacje skarbowe) as safe assets
- Wants data-driven allocation recommendations based on academic finance theory

## Problem Statement

Retail investors face several challenges:

1. **Risk Assessment**: Difficulty quantifying their true risk tolerance in a way that maps to portfolio theory
2. **Optimal Allocation**: No simple way to calculate the mathematically optimal split between stocks and bonds
3. **Regional Diversification**: Unclear how to weight different geographic regions (US, Europe, Japan, EM)
4. **Market Context**: Hard to stay current with valuations, volatility, and institutional views
5. **Contribution Decisions**: When adding money, unclear which assets to buy to maintain optimal allocation

## Functional Requirements

### FR1: Bond Position Entry
- **FR1.1**: User can enter Polish inflation-linked bond holdings in PLN
- **FR1.2**: System displays EUR equivalent using current EUR/PLN rate
- **FR1.3**: Bonds are treated as risk-free assets in the optimization

### FR2: Portfolio Import
- **FR2.1**: User can upload IBKR Activity Statement CSV to import ETF holdings
- **FR2.2**: User can manually enter ETF positions (ticker, value)
- **FR2.3**: System parses "Open Positions" section from IBKR CSV
- **FR2.4**: System extracts ticker, value, and currency for each position

### FR3: ETF Identification
- **FR3.1**: System identifies ETF details using AI (Claude)
- **FR3.2**: For each ticker, system determines: region, full name, ISIN, TER, accumulating status
- **FR3.3**: Supported regions: US, Europe, Japan, EM (Emerging Markets), Gold
- **FR3.4**: User can manually override any identified region
- **FR3.5**: System validates ETFs against constraints (accumulating, EUR, UCITS, TER < 0.50%)

### FR4: Risk Profile Assessment
- **FR4.1**: User completes 4-question CRRA survey to determine risk aversion coefficient
- **FR4.2**: Alternatively, user can directly input CRRA value (1-10 scale)
- **FR4.3**: System displays risk profile interpretation and typical investor comparison
- **FR4.4**: CRRA value determines optimal risky/safe asset split via formula: risky = 1/γ

### FR5: Market Data Gathering
- **FR5.1**: System fetches current market data via Claude AI
- **FR5.2**: Data includes: valuations (CAPE, P/E), volatility, dividend yields, institutional views
- **FR5.3**: System provides correlation matrix for asset classes
- **FR5.4**: Data is cached to avoid repeated API calls
- **FR5.5**: User can force refresh to get latest data
- **FR5.6**: System shows warning if using default correlations

### FR6: Portfolio Optimization
- **FR6.1**: System calculates optimal weights using Merton's CRRA utility optimization
- **FR6.2**: Optimization uses scipy SLSQP solver with constraints (weights sum to 1, non-negative)
- **FR6.3**: Output includes: optimal weights, expected return, volatility, Sharpe ratio, CRRA utility
- **FR6.4**: System shows risk contribution by asset class

### FR7: Gap Analysis
- **FR7.1**: System compares current allocation to optimal target
- **FR7.2**: For each region, shows: current %, target %, gap, priority (high/medium/consider/hold)
- **FR7.3**: Priority incorporates valuation signals and institutional views
- **FR7.4**: System identifies which positions to increase/decrease

### FR8: Contribution Allocation
- **FR8.1**: User enters contribution amount (new money to invest)
- **FR8.2**: System calculates which assets to buy to move toward optimal allocation
- **FR8.3**: Allocation considers which assets will be underweight AFTER contribution dilutes portfolio
- **FR8.4**: System respects minimum allocation threshold (e.g., €100 minimum per position)
- **FR8.5**: System shows post-allocation preview: how each position looks after contribution

### FR9: Portfolio Summary
- **FR9.1**: System shows total portfolio value (bonds + ETFs)
- **FR9.2**: System shows current vs target risky/bonds split
- **FR9.3**: System provides recommendation on whether to focus next contribution on bonds or ETFs

### FR10: Rebalancing Check
- **FR10.1**: System detects if any position is significantly overweight
- **FR10.2**: System provides sell recommendations for overweight positions
- **FR10.3**: System includes tax implications note (selling triggers capital gains)

## Non-Functional Requirements

### NFR1: Usability
- Guided workflow with clear step-by-step progression
- Mobile-responsive design
- Real-time validation and error messages

### NFR2: Performance
- Market data caching to reduce API latency
- Sub-second page transitions
- ETF identification completes within 10 seconds

### NFR3: Data Privacy
- No user data stored on server (stateless API)
- Portfolio data stored only in browser localStorage
- User controls when to clear stored data

### NFR4: Extensibility
- Claude prompts stored in configurable text files
- New regions can be added without code changes
- Correlation defaults can be updated without redeployment

## Constraints

### Technical Constraints
- ETFs must be UCITS-compliant
- ETFs must be EUR-denominated
- ETFs must be accumulating (not distributing)
- TER must be below 0.50%

### Business Constraints
- Relies on Claude AI for market data and ETF identification
- Requires Anthropic API key for backend operation
- Market data is AI-generated, not from financial data providers

## Success Metrics

1. User can complete full workflow (bonds → portfolio → risk → market data → results) in under 5 minutes
2. ETF region identification accuracy > 95%
3. Optimal allocation mathematically matches Merton's formula
4. Contribution allocation moves portfolio closer to target weights

## Out of Scope

- Real-time market data feeds
- Trade execution / broker integration
- Tax optimization / tax-loss harvesting
- Multi-currency support beyond EUR/PLN
- Individual stock analysis
- Bond selection recommendations
- Historical performance backtesting
