# Merton Share - Portfolio Optimization

A web application for optimal asset allocation between stocks and bonds using Merton's portfolio theory with CRRA (Constant Relative Risk Aversion) utility.

## Features

- **IBKR CSV Import**: Upload your Interactive Brokers Activity Statement CSV to import portfolio holdings
- **CRRA Risk Survey**: Interactive questionnaire to determine your risk aversion coefficient
- **AI-Powered Market Data**: Claude gathers current valuations, volatility, and institutional views
- **Merton Optimization**: Calculate optimal stock/bond allocation based on your risk profile
- **Contribution Calculator**: See recommended allocation for new investment contributions

## Tech Stack

**Backend:**
- Python 3.10+
- FastAPI
- Pydantic
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
│   │   ├── api/routes/       # API endpoints
│   │   ├── core/             # Business logic (merton_share, crra_survey)
│   │   ├── models/           # Pydantic models
│   │   ├── prompts/          # Configurable Claude prompts
│   │   └── services/         # Claude API service
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable components
│   │   ├── pages/            # Page components
│   │   ├── store/            # Zustand state management
│   │   └── types/            # TypeScript types
│   └── package.json
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

## How to Use

1. **Bonds Entry**: Enter your Polish inflation-linked bond holdings (optional)
2. **Portfolio Import**: Upload your IBKR Activity Statement CSV or manually enter ETF holdings
3. **Risk Profile**: Complete the CRRA survey to determine your risk tolerance
4. **Market Data**: Fetch current market valuations and institutional views via Claude
5. **Results**: View your optimal allocation and contribution recommendations

## IBKR CSV Export

To export your portfolio from Interactive Brokers:

1. Log in to IBKR Client Portal
2. Go to **Reports** > **Activity**
3. Select your date range
4. Choose **CSV** format
5. Download and upload to the app

The app parses the "Open Positions" section of the Activity Statement.

## Customizing Prompts

The Claude prompt for gathering market data can be customized without touching code:

Edit `backend/app/prompts/market_data.txt` to modify what data Claude collects and how it formats the response.

## Running Tests

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

## Theoretical Background

The optimizer implements Merton's optimal portfolio selection model:

```
α* = (μ - r) / (γσ²)
```

Where:
- **α*** = optimal fraction in risky assets
- **μ** = expected return of risky portfolio
- **r** = risk-free rate
- **γ** = coefficient of relative risk aversion (CRRA)
- **σ²** = variance of risky portfolio

For multiple assets:
```
α* = (1/γ) × Σ⁻¹(μ - r·1)
```

## ETF Constraints

The app validates ETF holdings against these requirements:
- Accumulating (not distributing)
- EUR-denominated
- UCITS-compliant
- TER < 0.50%

## License

MIT
