import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store';
import type { ETFHolding } from '../types';

const EXAMPLE_HOLDINGS: ETFHolding[] = [
  {
    ticker: 'ETFSP500',
    name: 'Amundi S&P 500 UCITS ETF EUR',
    valueEur: 15000,
    percentage: 45,
    isAccumulating: true,
    currencyDenomination: 'EUR',
    isUcits: true,
    ter: 0.0015,
  },
  {
    ticker: '4GLD',
    name: 'Xetra-Gold',
    valueEur: 8000,
    percentage: 24,
    isAccumulating: true,
    currencyDenomination: 'EUR',
    isUcits: true,
    ter: 0.0025,
  },
  {
    ticker: 'EUNK',
    name: 'iShares Core MSCI Europe UCITS ETF',
    valueEur: 10000,
    percentage: 31,
    isAccumulating: true,
    currencyDenomination: 'EUR',
    isUcits: true,
    ter: 0.0012,
  },
];

export default function PortfolioEntryPage() {
  const navigate = useNavigate();
  const { portfolio, setPortfolio, markStepComplete } = useAppStore();

  const [holdings, setHoldings] = useState<ETFHolding[]>(
    portfolio?.holdings ?? EXAMPLE_HOLDINGS
  );

  const addHolding = () => {
    setHoldings([
      ...holdings,
      {
        ticker: '',
        valueEur: 0,
        percentage: 0,
        isAccumulating: true,
        currencyDenomination: 'EUR',
        isUcits: true,
        ter: 0.002,
      },
    ]);
  };

  const updateHolding = (index: number, updates: Partial<ETFHolding>) => {
    const newHoldings = [...holdings];
    newHoldings[index] = { ...newHoldings[index], ...updates };
    setHoldings(newHoldings);
  };

  const removeHolding = (index: number) => {
    setHoldings(holdings.filter((_, i) => i !== index));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const totalValue = holdings.reduce((sum, h) => sum + h.valueEur, 0);

    // Recalculate percentages
    const updatedHoldings = holdings.map((h) => ({
      ...h,
      percentage: totalValue > 0 ? (h.valueEur / totalValue) * 100 : 0,
    }));

    setPortfolio({
      holdings: updatedHoldings,
      totalValueEur: totalValue,
    });
    markStepComplete('portfolio');
    navigate('/risk-profile');
  };

  const totalValue = holdings.reduce((sum, h) => sum + h.valueEur, 0);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">ETF Portfolio</h2>
        <p className="mt-1 text-gray-500">
          Enter your current ETF holdings. Screenshot upload coming in Phase 2.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {holdings.map((holding, index) => (
          <div key={index} className="card">
            <div className="flex justify-between items-start mb-4">
              <span className="text-sm font-medium text-gray-500">
                Position {index + 1}
              </span>
              {holdings.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeHolding(index)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  Remove
                </button>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Ticker</label>
                <input
                  type="text"
                  value={holding.ticker}
                  onChange={(e) =>
                    updateHolding(index, { ticker: e.target.value.toUpperCase() })
                  }
                  className="input"
                  placeholder="e.g., ETFSP500"
                  required
                />
              </div>

              <div>
                <label className="label">Value (EUR)</label>
                <input
                  type="number"
                  value={holding.valueEur || ''}
                  onChange={(e) =>
                    updateHolding(index, {
                      valueEur: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="input"
                  min="0"
                  step="100"
                  required
                />
              </div>

              <div>
                <label className="label">TER (%)</label>
                <input
                  type="number"
                  value={(holding.ter * 100).toFixed(2)}
                  onChange={(e) =>
                    updateHolding(index, {
                      ter: (parseFloat(e.target.value) || 0) / 100,
                    })
                  }
                  className="input"
                  min="0"
                  max="1"
                  step="0.01"
                />
              </div>

              <div className="flex items-end gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={holding.isAccumulating}
                    onChange={(e) =>
                      updateHolding(index, { isAccumulating: e.target.checked })
                    }
                    className="rounded"
                  />
                  <span className="text-sm">Accumulating</span>
                </label>

                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={holding.isUcits}
                    onChange={(e) =>
                      updateHolding(index, { isUcits: e.target.checked })
                    }
                    className="rounded"
                  />
                  <span className="text-sm">UCITS</span>
                </label>
              </div>
            </div>

            {holding.ter > 0.005 && (
              <div className="mt-2 text-sm text-amber-600">
                Warning: TER exceeds 0.50% threshold
              </div>
            )}
          </div>
        ))}

        <button
          type="button"
          onClick={addHolding}
          className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-colors"
        >
          + Add ETF Position
        </button>

        <div className="card bg-gray-50">
          <div className="flex justify-between items-center">
            <span className="font-medium text-gray-700">Total Portfolio Value</span>
            <span className="text-2xl font-bold text-primary-600">
              €{totalValue.toLocaleString()}
            </span>
          </div>
        </div>

        <button type="submit" className="btn btn-primary w-full">
          Continue to Risk Profile
        </button>
      </form>
    </div>
  );
}
