import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store';
import CSVUploader from '../components/portfolio/CSVUploader';
import type { ETFHolding } from '../types';

type InputMethod = 'manual' | 'csv';

const EMPTY_HOLDING: ETFHolding = {
  ticker: '',
  valueEur: 0,
  percentage: 0,
  isAccumulating: true,
  currencyDenomination: 'EUR',
  isUcits: true,
  ter: 0.002,
};

export default function PortfolioEntryPage() {
  const navigate = useNavigate();
  const { portfolio, setPortfolio, markStepComplete } = useAppStore();

  const [method, setMethod] = useState<InputMethod>('csv');
  const [holdings, setHoldings] = useState<ETFHolding[]>(
    portfolio?.holdings ?? []
  );
  const [error, setError] = useState<string | null>(null);
  const [csvProcessed, setCsvProcessed] = useState(false);

  const addHolding = () => {
    setHoldings([...holdings, { ...EMPTY_HOLDING }]);
  };

  const updateHolding = (index: number, updates: Partial<ETFHolding>) => {
    const newHoldings = [...holdings];
    newHoldings[index] = { ...newHoldings[index], ...updates };
    setHoldings(newHoldings);
  };

  const removeHolding = (index: number) => {
    setHoldings(holdings.filter((_, i) => i !== index));
  };

  const handleCSVExtracted = (
    extractedHoldings: Array<{
      ticker: string;
      valueEur: number;
      percentage: number;
      currencyDenomination: string;
      region?: string;
      name?: string;
      isin?: string;
    }>,
    totalValue: number
  ) => {
    const newHoldings: ETFHolding[] = extractedHoldings.map((h) => ({
      ticker: h.ticker,
      name: h.name,
      isin: h.isin,
      region: h.region,
      valueEur: h.valueEur,
      percentage: h.percentage,
      isAccumulating: true,
      currencyDenomination: h.currencyDenomination,
      isUcits: true,
      ter: 0.002,
    }));
    setHoldings(newHoldings);
    setCsvProcessed(true);
    setError(null);
  };

  const handleCSVError = (err: string) => {
    setError(err);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (holdings.length === 0) {
      setError('Please add at least one ETF holding');
      return;
    }

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
          Upload your IBKR CSV export or manually enter your ETF holdings.
        </p>
      </div>

      {/* Method selector */}
      <div className="flex gap-4">
        <button
          onClick={() => setMethod('csv')}
          className={`flex-1 py-3 px-4 rounded-lg border-2 transition-colors ${
            method === 'csv'
              ? 'border-primary-500 bg-primary-50 text-primary-700'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <div className="font-medium">IBKR CSV Upload</div>
          <div className="text-sm text-gray-500">Import from Activity Statement</div>
        </button>
        <button
          onClick={() => setMethod('manual')}
          className={`flex-1 py-3 px-4 rounded-lg border-2 transition-colors ${
            method === 'manual'
              ? 'border-primary-500 bg-primary-50 text-primary-700'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <div className="font-medium">Manual Entry</div>
          <div className="text-sm text-gray-500">Type in your holdings</div>
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* CSV uploader */}
      {method === 'csv' && !csvProcessed && (
        <CSVUploader
          onPortfolioExtracted={handleCSVExtracted}
          onError={handleCSVError}
        />
      )}

      {/* Holdings form - show if manual OR after CSV processed */}
      {(method === 'manual' || csvProcessed || holdings.length > 0) && (
        <form onSubmit={handleSubmit} className="space-y-4">
          {csvProcessed && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
              Portfolio imported from CSV. Review and edit if needed.
            </div>
          )}

          {holdings.map((holding, index) => (
            <div key={index} className="card">
              <div className="flex justify-between items-start mb-4">
                <span className="text-sm font-medium text-gray-500">
                  Position {index + 1}
                </span>
                {holdings.length > 0 && (
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
                    step="0.01"
                    required
                  />
                </div>

                {holding.name && (
                  <div className="col-span-2">
                    <label className="label">Name</label>
                    <input
                      type="text"
                      value={holding.name}
                      onChange={(e) => updateHolding(index, { name: e.target.value })}
                      className="input"
                    />
                  </div>
                )}

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

          {holdings.length > 0 && (
            <>
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
            </>
          )}
        </form>
      )}
    </div>
  );
}
