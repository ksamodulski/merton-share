# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  CLIENT                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        React SPA (Vite + TS)                          │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐  │  │
│  │  │   Pages     │ │ Components  │ │   Store     │ │    Services     │  │  │
│  │  │             │ │             │ │  (Zustand)  │ │                 │  │  │
│  │  │ - Bonds     │ │ - CSV       │ │             │ │ - api.ts        │  │  │
│  │  │ - Portfolio │ │   Uploader  │ │ localStorage│ │   (fetch calls) │  │  │
│  │  │ - CRRA      │ │ - CRRA      │ │ persistence │ │                 │  │  │
│  │  │ - Market    │ │   Survey    │ │             │ │                 │  │  │
│  │  │ - Results   │ │ - Layout    │ │             │ │                 │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP/REST
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  SERVER                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         FastAPI Backend                               │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                        API Routes                                │  │  │
│  │  │  /portfolio    /crra    /optimize    /market-data               │  │  │
│  │  │  - parse-csv   - calc   - optimize   - gather                   │  │  │
│  │  │  - lookup-etfs - scale  - gap        - cached                   │  │  │
│  │  │  - validate    - interp - allocate   - defaults                 │  │  │
│  │  │                         - rebalance                              │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                        │  │
│  │              ┌───────────────┼───────────────┐                        │  │
│  │              ▼               ▼               ▼                        │  │
│  │  ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐              │  │
│  │  │     Models      │ │    Core     │ │    Services     │              │  │
│  │  │   (Pydantic)    │ │  (Business  │ │                 │              │  │
│  │  │                 │ │   Logic)    │ │ Claude Service  │──────┐       │  │
│  │  │ - portfolio.py  │ │             │ │                 │      │       │  │
│  │  │ - crra.py       │ │ - merton    │ │ - gather_market │      │       │  │
│  │  │ - optimization  │ │   _share.py │ │ - lookup_etfs   │      │       │  │
│  │  │ - market_data   │ │ - crra      │ │                 │      │       │  │
│  │  │                 │ │   _survey   │ │                 │      │       │  │
│  │  └─────────────────┘ └─────────────┘ └─────────────────┘      │       │  │
│  │                                                                │       │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │       │  │
│  │  │                    Prompts (txt files)                   │  │       │  │
│  │  │            market_data.txt    etf_lookup.txt             │  │       │  │
│  │  └─────────────────────────────────────────────────────────┘  │       │  │
│  └───────────────────────────────────────────────────────────────┘       │  │
└──────────────────────────────────────────────────────────────────────────┘  │
                                                                               │
                                      ┌────────────────────────────────────────┘
                                      │ Anthropic API
                                      ▼
                          ┌───────────────────────┐
                          │    Claude AI (LLM)    │
                          │                       │
                          │ - Market data lookup  │
                          │ - ETF identification  │
                          │   (region, name,      │
                          │    ISIN, TER)         │
                          └───────────────────────┘
```

## Data Flow

### 1. Portfolio Import Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  User    │    │ CSV      │    │ Backend  │    │ Claude   │    │ Frontend │
│ uploads  │───▶│ Uploader │───▶│ parse-csv│───▶│ lookup-  │───▶│ displays │
│ CSV file │    │          │    │          │    │ etfs     │    │ holdings │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                     │               │
                                     │               │
                                     ▼               ▼
                              ┌──────────┐    ┌──────────┐
                              │ Parsed   │    │ ETF      │
                              │ holdings │    │ metadata │
                              │ (ticker, │    │ (region, │
                              │  value)  │    │  name,   │
                              └──────────┘    │  ISIN)   │
                                              └──────────┘
```

### 2. Optimization Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Holdings │    │   CRRA   │    │  Market  │    │ Optimize │    │   Gap    │
│ by region│───▶│   γ=3.5  │───▶│   Data   │───▶│  scipy   │───▶│ Analysis │
└──────────┘    └──────────┘    └──────────┘    │  SLSQP   │    └──────────┘
                                     │          └──────────┘         │
                                     │               │               │
                                     ▼               ▼               ▼
                              ┌──────────┐    ┌──────────┐    ┌──────────┐
                              │ Returns  │    │ Optimal  │    │ Current  │
                              │ Volatility│   │ Weights  │    │ vs Target│
                              │ Correlat.│    │ per region│   │   gaps   │
                              └──────────┘    └──────────┘    └──────────┘
```

### 3. Contribution Allocation Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Gap      │    │ Contrib. │    │ Allocate │    │ Post-    │
│ Analysis │───▶│ Amount   │───▶│ to under-│───▶│ alloc.   │
│          │    │ (€5000)  │    │ weight   │    │ preview  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                     │               │
                                     ▼               ▼
                              ┌──────────┐    ┌──────────┐
                              │ Buy list │    │ All pos. │
                              │ €2500 EM │    │ after    │
                              │ €1500 JP │    │ contrib. │
                              │ €1000 EU │    │          │
                              └──────────┘    └──────────┘
```

## Component Details

### Frontend Components

| Component | Purpose |
|-----------|---------|
| `BondEntryPage` | Enter Polish inflation-linked bond holdings |
| `PortfolioEntryPage` | 3-step flow: Import → Identify → Review |
| `CRRAPage` | Risk survey or direct CRRA input |
| `MarketDataPage` | Display valuations, volatility, correlations |
| `ResultsPage` | Show optimization, gap analysis, allocation |
| `CSVUploader` | Drag-drop CSV parsing |
| `CRRAQuestionnaire` | 4-question risk assessment |

### Backend Routes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/portfolio/parse-csv` | POST | Parse IBKR CSV file |
| `/portfolio/lookup-etfs` | POST | Identify ETF metadata via Claude |
| `/crra/calculate` | POST | Calculate CRRA from survey responses |
| `/crra/interpret` | POST | Get risk profile for CRRA value |
| `/market-data/gather` | POST | Fetch market data via Claude |
| `/optimize` | POST | Run Merton optimization |
| `/optimize/gap-analysis` | POST | Compare current vs optimal |
| `/optimize/allocate` | POST | Allocate contribution amount |
| `/optimize/rebalance` | POST | Check for rebalancing needs |

### Core Algorithms

#### Merton Optimization (`merton_share.py`)

Uses CRRA (Constant Relative Risk Aversion) utility:

```
U(W) = W^(1-γ) / (1-γ)    for γ ≠ 1
U(W) = ln(W)              for γ = 1
```

Optimal allocation maximizes expected utility:
```
max E[U(W)] = max [μ_p - (γ/2)σ_p²]
```

Where:
- μ_p = portfolio expected return
- σ_p = portfolio volatility
- γ = risk aversion coefficient

#### CRRA Survey (`crra_survey.py`)

Estimates γ from 4 behavioral questions:
1. Maximum acceptable loss (maps to loss aversion)
2. Portfolio risk percentage willing to take
3. Preferred stock allocation
4. Lottery choice (certainty equivalent)

## State Management

```
┌─────────────────────────────────────────────────────────────┐
│                    Zustand Store                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │   bonds     │ │  portfolio  │ │      marketData         ││
│  │             │ │             │ │                         ││
│  │ amountPln   │ │ holdings[]  │ │ valuations[]            ││
│  │ yieldRate   │ │ totalValue  │ │ volatility[]            ││
│  │ amountEur   │ │             │ │ correlations{}          ││
│  └─────────────┘ └─────────────┘ │ institutionalViews[]    ││
│                                  │ riskFreeRate            ││
│  ┌─────────────┐ ┌─────────────┐ └─────────────────────────┘│
│  │    crra     │ │completedSteps│                          │
│  │             │ │              │                          │
│  │ value: 3.5  │ │ bonds: true  │     Persisted to         │
│  │ profile: {} │ │ portfolio: ✓ │     localStorage         │
│  │             │ │ risk: true   │                          │
│  └─────────────┘ └──────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React 18 | UI framework |
| Frontend | TypeScript | Type safety |
| Frontend | Vite | Build tool |
| Frontend | Tailwind CSS | Styling |
| Frontend | Zustand | State management |
| Backend | Python 3.10+ | Runtime |
| Backend | FastAPI | Web framework |
| Backend | Pydantic | Data validation |
| Backend | scipy | Optimization solver |
| Backend | numpy | Matrix operations |
| AI | Claude (Anthropic) | Market data, ETF lookup |

## Security Considerations

1. **No persistent storage**: Server is stateless, no database
2. **Client-side data**: Portfolio stored in browser localStorage only
3. **API key**: Anthropic key stored in server .env, never exposed to client
4. **CORS**: Configured for localhost development
5. **Input validation**: All inputs validated via Pydantic models
