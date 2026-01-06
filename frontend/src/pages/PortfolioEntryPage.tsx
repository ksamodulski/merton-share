import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store';
import { portfolioApi } from '../services/api';
import CSVUploader from '../components/portfolio/CSVUploader';
import type { ETFHolding } from '../types';

type InputMethod = 'manual' | 'csv';
type Step = 'import' | 'identify' | 'review';

const REGIONS = ['US', 'Europe', 'Japan', 'EM', 'Gold'] as const;

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
  const [step, setStep] = useState<Step>(portfolio?.holdings?.length ? 'review' : 'import');
  const [holdings, setHoldings] = useState<ETFHolding[]>(portfolio?.holdings ?? []);
  const [error, setError] = useState<string | null>(null);
  const [isIdentifying, setIsIdentifying] = useState(false);
  const [identificationComplete, setIdentificationComplete] = useState(false);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  // Manual entry
  const addHolding = () => {
    setHoldings([...holdings, { ...EMPTY_HOLDING }]);
    setStep('review');
  };

  const updateHolding = (index: number, updates: Partial<ETFHolding>) => {
    const newHoldings = [...holdings];
    newHoldings[index] = { ...newHoldings[index], ...updates };
    setHoldings(newHoldings);
  };

  const removeHolding = (index: number) => {
    setHoldings(holdings.filter((_, i) => i !== index));
    if (holdings.length <= 1) {
      setStep('import');
    }
  };

  // CSV import handler
  const handleCSVParsed = (
    parsedHoldings: Array<{
      ticker: string;
      valueEur: number;
      percentage: number;
      currencyDenomination: string;
    }>,
    _totalValue: number
  ) => {
    const newHoldings: ETFHolding[] = parsedHoldings.map((h) => ({
      ticker: h.ticker,
      valueEur: h.valueEur,
      percentage: h.percentage,
      isAccumulating: true,
      currencyDenomination: h.currencyDenomination,
      isUcits: true,
      ter: 0.002,
      // No region yet - will be identified
    }));
    setHoldings(newHoldings);
    setStep('identify');
    setIdentificationComplete(false);
    setError(null);
  };

  // ETF identification via Claude
  const handleIdentifyETFs = async () => {
    setIsIdentifying(true);
    setError(null);

    try {
      const tickers = holdings.map((h) => h.ticker);
      const result = await portfolioApi.lookupEtfs(tickers);

      // Build lookup map
      const etfMap: Record<string, typeof result.etfs[0]> = {};
      for (const etf of result.etfs) {
        etfMap[etf.ticker] = etf;
      }

      // Enrich holdings with metadata
      const enrichedHoldings = holdings.map((h) => {
        const metadata = etfMap[h.ticker];
        if (metadata) {
          return {
            ...h,
            region: metadata.region,
            name: metadata.name,
            isin: metadata.isin,
            ter: metadata.ter ?? h.ter,
            isAccumulating: metadata.is_accumulating ?? h.isAccumulating,
          };
        }
        return h;
      });

      setHoldings(enrichedHoldings);
      setIdentificationComplete(true);
      setStep('review');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to identify ETFs');
    } finally {
      setIsIdentifying(false);
    }
  };

  // Submit portfolio
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (holdings.length === 0) {
      setError('Please add at least one ETF holding');
      return;
    }

    // Check for missing regions
    const missingRegions = holdings.filter((h) => !h.region);
    if (missingRegions.length > 0) {
      setError(`Please identify or set regions for all holdings. Missing: ${missingRegions.map((h) => h.ticker).join(', ')}`);
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
  const unidentifiedCount = holdings.filter((h) => !h.region).length;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">ETF Portfolio</h2>
        <p className="mt-1 text-gray-500">
          Import your holdings and identify ETF details for accurate region mapping.
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 text-sm">
        <span className={`px-3 py-1 rounded-full ${step === 'import' ? 'bg-primary-100 text-primary-700 font-medium' : 'bg-gray-100 text-gray-600'}`}>
          1. Import
        </span>
        <span className="text-gray-300">→</span>
        <span className={`px-3 py-1 rounded-full ${step === 'identify' ? 'bg-primary-100 text-primary-700 font-medium' : 'bg-gray-100 text-gray-600'}`}>
          2. Identify
        </span>
        <span className="text-gray-300">→</span>
        <span className={`px-3 py-1 rounded-full ${step === 'review' ? 'bg-primary-100 text-primary-700 font-medium' : 'bg-gray-100 text-gray-600'}`}>
          3. Review
        </span>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Step 1: Import */}
      {step === 'import' && (
        <div className="space-y-4">
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

          {method === 'csv' && (
            <CSVUploader
              onPortfolioParsed={handleCSVParsed}
              onError={(err) => setError(err)}
            />
          )}

          {method === 'manual' && (
            <button
              onClick={addHolding}
              className="w-full py-4 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-colors"
            >
              + Add ETF Position
            </button>
          )}
        </div>
      )}

      {/* Step 2: Identify - show after import */}
      {step === 'identify' && holdings.length > 0 && (
        <div className="space-y-4">
          <div className="card bg-blue-50 border-blue-200">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h3 className="font-medium text-blue-900">Imported {holdings.length} positions</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Click "Identify ETF Details" to fetch region, name, and metadata for each ticker using AI.
                </p>
              </div>
            </div>
          </div>

          {/* Preview table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-2 font-medium">Ticker</th>
                  <th className="py-2 font-medium text-right">Value</th>
                  <th className="py-2 font-medium text-right">%</th>
                  <th className="py-2 font-medium">Currency</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="py-2 font-mono font-medium">{h.ticker}</td>
                    <td className="py-2 text-right">€{h.valueEur.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                    <td className="py-2 text-right text-gray-600">{h.percentage.toFixed(1)}%</td>
                    <td className="py-2 text-gray-500">{h.currencyDenomination}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            onClick={handleIdentifyETFs}
            disabled={isIdentifying}
            className="btn btn-primary w-full flex items-center justify-center gap-2"
          >
            {isIdentifying ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                Identifying ETFs...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Identify ETF Details
              </>
            )}
          </button>

          <button
            onClick={() => setStep('review')}
            className="w-full text-sm text-gray-500 hover:text-gray-700"
          >
            Skip identification and set regions manually →
          </button>
        </div>
      )}

      {/* Step 3: Review */}
      {step === 'review' && holdings.length > 0 && (
        <form onSubmit={handleSubmit} className="space-y-4">
          {identificationComplete && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              ETF details identified. Review and adjust if needed.
            </div>
          )}

          {unidentifiedCount > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              {unidentifiedCount} position(s) need region assignment.
              {!identificationComplete && (
                <button
                  type="button"
                  onClick={() => setStep('identify')}
                  className="underline ml-1"
                >
                  Identify now
                </button>
              )}
            </div>
          )}

          {/* Holdings table */}
          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b text-left text-gray-500">
                  <th className="py-3 px-4 font-medium">Ticker</th>
                  <th className="py-3 px-4 font-medium">Region</th>
                  <th className="py-3 px-4 font-medium text-right">Value</th>
                  <th className="py-3 px-4 font-medium text-right">%</th>
                  <th className="py-3 px-4 font-medium text-right">TER</th>
                  <th className="py-3 px-4"></th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h, index) => (
                  <>
                    <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <button
                          type="button"
                          onClick={() => setExpandedRow(expandedRow === index ? null : index)}
                          className="flex items-center gap-2 text-left"
                        >
                          <span className="font-mono font-medium">{h.ticker}</span>
                          {h.name && (
                            <svg
                              className={`w-4 h-4 text-gray-400 transition-transform ${expandedRow === index ? 'rotate-180' : ''}`}
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          )}
                        </button>
                      </td>
                      <td className="py-3 px-4">
                        <select
                          value={h.region || ''}
                          onChange={(e) => updateHolding(index, { region: e.target.value || undefined })}
                          className={`px-2 py-1 rounded border text-sm ${
                            h.region
                              ? 'border-gray-200 bg-white'
                              : 'border-amber-300 bg-amber-50 text-amber-700'
                          }`}
                        >
                          <option value="">Select...</option>
                          {REGIONS.map((r) => (
                            <option key={r} value={r}>{r}</option>
                          ))}
                        </select>
                      </td>
                      <td className="py-3 px-4 text-right font-medium">
                        €{h.valueEur.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-600">
                        {h.percentage.toFixed(1)}%
                      </td>
                      <td className="py-3 px-4 text-right text-gray-500">
                        {(h.ter * 100).toFixed(2)}%
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => removeHolding(index)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                    {/* Expanded details row */}
                    {expandedRow === index && (h.name || h.isin) && (
                      <tr key={`${index}-expanded`} className="bg-gray-50">
                        <td colSpan={6} className="px-4 py-2 text-sm text-gray-600">
                          <div className="flex flex-wrap gap-4">
                            {h.name && (
                              <div>
                                <span className="text-gray-400">Name:</span> {h.name}
                              </div>
                            )}
                            {h.isin && (
                              <div>
                                <span className="text-gray-400">ISIN:</span> <span className="font-mono">{h.isin}</span>
                              </div>
                            )}
                            <div>
                              <span className="text-gray-400">Accumulating:</span> {h.isAccumulating ? 'Yes' : 'No'}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>

          {/* Add position button */}
          <button
            type="button"
            onClick={addHolding}
            className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-colors text-sm"
          >
            + Add ETF Position
          </button>

          {/* Summary and submit */}
          <div className="card bg-gray-50">
            <div className="flex justify-between items-center">
              <span className="font-medium text-gray-700">Total Portfolio Value</span>
              <span className="text-2xl font-bold text-primary-600">
                €{totalValue.toLocaleString()}
              </span>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setStep('import')}
              className="btn bg-gray-100 text-gray-700 hover:bg-gray-200"
            >
              ← Re-import
            </button>
            {!identificationComplete && unidentifiedCount > 0 && (
              <button
                type="button"
                onClick={handleIdentifyETFs}
                disabled={isIdentifying}
                className="btn bg-blue-100 text-blue-700 hover:bg-blue-200 flex items-center gap-2"
              >
                {isIdentifying ? (
                  <>
                    <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                    Identifying...
                  </>
                ) : (
                  'Identify ETFs'
                )}
              </button>
            )}
            <button type="submit" className="btn btn-primary flex-1">
              Continue to Risk Profile →
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
