# Merton Share - Portfolio Optimization

A web application for optimal asset allocation between stocks and bonds using Merton's portfolio theory with CRRA (Constant Relative Risk Aversion) utility.

## Features

- **IBKR CSV Import**: Upload your Interactive Brokers Activity Statement CSV to import portfolio holdings
- **AI-Powered ETF Identification**: Claude identifies region, name, ISIN, and TER for each ticker
- **CRRA Risk Survey**: Interactive questionnaire to determine your risk aversion coefficient
- **AI-Powered Market Data**: Claude gathers current valuations, volatility, correlations, and institutional views
- **Merton Optimization**: Calculate optimal regional weights using scipy SLSQP solver
- **Gap Analysis**: Compare current allocation vs optimal with priority signals
- **Contribution Calculator**: See recommended allocation for new investment contributions
- **Portfolio Summary**: View current vs target risky/bonds split with recommendations

## Documentation

- [Business Requirements](docs/business_requirements.md) - Detailed functional and non-functional requirements
- [Architecture](docs/architecture.md) - System design, data flows, and component details

## Tech Stack

**Backend:**
- Python 3.10+
- FastAPI
- Pydantic
- scipy (SLSQP optimizer)
- Anthropic Claude API

**Frontend:**
- React 18 + TypeScript
- Vite
- Tailwind CSS
- Zustand (state management with localStorage persistence)

## Project Structure

```
merton-share/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # API endpoints (portfolio, crra, optimize, market-data)
│   │   ├── core/             # Business logic (merton_share, crra_survey)
│   │   ├── models/           # Pydantic models
│   │   ├── prompts/          # Configurable Claude prompts
│   │   └── services/         # Claude API service
│   ├── tests/                # pytest tests
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable components (CSVUploader, CRRA survey)
│   │   ├── pages/            # Page components (5-step workflow)
│   │   ├── services/         # API client
│   │   ├── store/            # Zustand state management
│   │   └── types/            # TypeScript types
│   └── package.json
├── docs/
│   ├── architecture.md       # System architecture
│   └── business_requirements.md
└── readme.md
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Anthropic API key

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy the example env file and add your API key
cp .env.example .env
# Edit .env and add your Anthropic API key

# Run the server
uvicorn app.main:app --reload --port 8000
```

API documentation is available at `http://localhost:8000/docs` (Swagger UI).

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`

## Workflow

The application guides you through a 5-step workflow:

### Step 1: Bonds Entry
Enter your Polish inflation-linked bond holdings (optional). These are treated as risk-free assets in the optimization.

> **Note:** Polish inflation-linked bonds carry minor sovereign and liquidity risk but are treated as risk-free for optimization purposes. This simplification is acceptable for most retail portfolios.

### Step 2: Portfolio Import
Three-phase process:
1. **Import**: Upload IBKR CSV or manually enter holdings
2. **Identify**: Click "Identify ETF Details" to have Claude recognize each ticker
3. **Review**: Verify regions (US, Europe, Japan, EM, Gold) with dropdown overrides

### Step 3: Risk Profile
Complete the 4-question CRRA survey or directly input your CRRA value (1-10). Your CRRA (γ) is used in:
- **Within-risky optimization**: Full Merton CRRA utility maximization across regions
- **Bonds/risky target**: Uses `1/γ` heuristic (a common financial planning approximation)
- Higher γ → more conservative allocation

### Step 4: Market Data
Fetch current market data via Claude:
- Valuations (CAPE, Forward P/E) by region
- Volatility estimates
- Correlation matrix (with warning if using defaults)
- Institutional views (overweight/neutral/underweight)

### Step 5: Results
View your personalized results:
- **Portfolio Summary**: Total value, current vs target risky/bonds split
- **Optimal Weights**: Target allocation by region
- **Gap Analysis**: Current vs target with priority signals
- **Contribution Allocation**: Enter amount to see buy recommendations
- **Post-Allocation Preview**: How all positions look after contribution

## IBKR CSV Export

To export your portfolio from Interactive Brokers:

1. Log in to IBKR Client Portal
2. Go to **Reports** > **Activity**
3. Select your date range
4. Choose **CSV** format
5. Download and upload to the app

The app parses the "Open Positions" section of the Activity Statement.

## Customizing Prompts

Claude prompts are stored in configurable text files:

- `backend/app/prompts/market_data.txt` - Market data gathering prompt
- `backend/app/prompts/etf_lookup.txt` - ETF identification prompt

Edit these to modify what data Claude collects and how it formats responses.

## Running Tests

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

## Theoretical Background

The optimizer implements Merton's optimal portfolio selection model with CRRA utility:

**Utility Function:**
```
U(W) = W^(1-γ) / (1-γ)    for γ ≠ 1
```

**Optimization Objective:**
```
max E[U] ≈ max [μ_p - (γ/2)σ_p²]
```

Where:
- **μ_p** = portfolio expected return
- **σ_p** = portfolio volatility
- **γ** = coefficient of relative risk aversion (CRRA)

**Optimal Risky Asset Fraction (single asset case):**
```
α* = (μ - r) / (γσ²)
```

**Multi-Asset Case:**
```
α* = (1/γ) × Σ⁻¹(μ - r·1)
```

Where Σ is the covariance matrix.

## ETF Constraints

The app validates ETF holdings against these requirements:
- Accumulating (not distributing)
- EUR-denominated
- UCITS-compliant
- TER < 0.50%

## Supported Regions

| Region | Description | Examples |
|--------|-------------|----------|
| US | S&P 500, NASDAQ, US total market | CSPX, VUAA |
| Europe | MSCI Europe, Stoxx 600 | MEUD, SXR1 |
| Japan | MSCI Japan, Nikkei, TOPIX | IJPA |
| EM | MSCI Emerging Markets | IEMA |
| Gold | Gold ETFs, precious metals | 4GLD |

> **Note on Gold:** Gold is included primarily for diversification benefits (low correlation with equities) rather than expected returns. Its expected return is estimated by Claude based on historical trends and market conditions.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/portfolio/parse-csv` | POST | Parse IBKR CSV |
| `/api/v1/portfolio/lookup-etfs` | POST | Identify ETF metadata |
| `/api/v1/crra/calculate` | POST | Calculate CRRA from survey |
| `/api/v1/crra/interpret` | POST | Get profile for CRRA value |
| `/api/v1/market-data/gather` | POST | Fetch market data |
| `/api/v1/optimize` | POST | Run optimization |
| `/api/v1/optimize/gap-analysis` | POST | Get gap analysis |
| `/api/v1/optimize/allocate` | POST | Allocate contribution |

Full API documentation at `/docs` when backend is running.

## Parameter Bounds

The optimizer enforces these constraints:

| Parameter | Range | Enforcement |
|-----------|-------|-------------|
| CRRA (γ) | 1.0 - 10.0 | UI slider limits |
| Asset weights | 0% - 50% | Optimizer constraint (prevents concentration) |
| Total allocation | 100% | Sum constraint (no leverage or shorting) |

## Technical Notes

**Risk-Free Rate:** The optimizer uses a default risk-free rate (2.5%) for Sharpe ratio calculations. The bonds/risky split uses the `1/γ` heuristic which doesn't directly use the risk-free rate.

**Correlation Matrix:** If Claude doesn't return correlations, realistic defaults are used (e.g., US-Europe: 0.85, Japan-US: 0.65, Gold-Equities: ~0.05-0.15). A warning is displayed when using defaults.

## License

MIT
