import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store';
import type { MarketData } from '../types';

export default function MarketDataPage() {
  const navigate = useNavigate();
  const {
    marketData,
    setMarketData,
    markStepComplete,
    setMarketDataLoading,
    marketDataLoading,
  } = useAppStore();
  const [error, setError] = useState<string | null>(null);

  const handleFetchMarketData = async () => {
    setError(null);
    setMarketDataLoading(true);

    try {
      const response = await fetch('/api/v1/market-data/gather', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force_refresh: true }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to fetch market data');
      }

      const data = await response.json();

      // Convert to frontend format
      const marketData: MarketData = {
        valuations: data.valuations.map((v: Record<string, unknown>) => ({
          region: v.region,
          cape: v.cape,
          forwardPe: v.forward_pe,
          dividendYield: v.dividend_yield,
          source: v.source,
          date: v.date,
        })),
        volatility: data.volatility.map((v: Record<string, unknown>) => ({
          asset: v.asset,
          impliedVol: v.implied_vol,
          realizedVol1Y: v.realized_vol_1y,
          source: v.source,
        })),
        institutionalViews: data.institutional_views.map((v: Record<string, unknown>) => ({
          region: v.region,
          stance: v.stance,
          sources: v.sources,
          keyDrivers: v.key_drivers,
        })),
        expectedReturns: data.expected_returns?.map((r: Record<string, unknown>) => ({
          region: r.region,
          return: r.return,
          rationale: r.rationale,
        })),
        correlations: data.correlations ? {
          assets: data.correlations.assets,
          matrix: data.correlations.matrix,
        } : undefined,
        riskFreeRate: data.risk_free_rate,
        eurPlnRate: data.eur_pln_rate,
        fetchedAt: data.fetched_at,
        sources: data.sources,
      };

      setMarketData(marketData);
      markStepComplete('market-data');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch market data');
    } finally {
      setMarketDataLoading(false);
    }
  };

  const handleContinue = () => {
    navigate('/results');
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Market Data</h2>
        <p className="mt-1 text-gray-500">
          Fetch current market valuations, volatility, and institutional views using Claude.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="card">
        <div className="flex gap-3 mb-6">
          <button
            onClick={handleFetchMarketData}
            disabled={marketDataLoading}
            className="btn btn-primary"
          >
            {marketDataLoading ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
                Fetching with Claude...
              </span>
            ) : (
              'Fetch Live Data'
            )}
          </button>
        </div>

        {marketDataLoading && (
          <div className="text-center py-8 text-gray-500">
            <p>Claude is gathering current market data...</p>
            <p className="text-sm mt-1">This may take a few seconds.</p>
          </div>
        )}

        {marketData && !marketDataLoading && (
          <div className="space-y-6">
            {/* Valuations Table */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Valuations</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Region</th>
                      <th className="px-4 py-2 text-right cursor-help" title="Cyclically Adjusted P/E (Shiller P/E). Price ÷ 10-year avg earnings. Lower = cheaper.">CAPE</th>
                      <th className="px-4 py-2 text-right cursor-help" title="Forward P/E. Price ÷ expected next-12-month earnings. Lower = cheaper.">Fwd P/E</th>
                      <th className="px-4 py-2 text-right cursor-help" title="Dividend Yield. Annual dividends ÷ price. Higher = more income.">Div Yield</th>
                      <th className="px-4 py-2 text-left">Source</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {marketData.valuations.map((v) => (
                      <tr key={v.region}>
                        <td className="px-4 py-2 font-medium">{v.region}</td>
                        <td className="px-4 py-2 text-right">{v.cape ?? '-'}</td>
                        <td className="px-4 py-2 text-right">{v.forwardPe ?? '-'}</td>
                        <td className="px-4 py-2 text-right">
                          {(v.dividendYield * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-2 text-gray-500 text-xs">{v.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Volatility Table */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Volatility</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Asset</th>
                      <th className="px-4 py-2 text-right cursor-help" title="Market's expected future volatility from options prices (VIX, VSTOXX). Forward-looking.">Implied Vol</th>
                      <th className="px-4 py-2 text-right cursor-help" title="Actual historical volatility measured over the past year. Backward-looking.">1Y Realized</th>
                      <th className="px-4 py-2 text-left">Source</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {marketData.volatility.map((v) => (
                      <tr key={v.asset}>
                        <td className="px-4 py-2 font-medium">{v.asset}</td>
                        <td className="px-4 py-2 text-right">
                          {v.impliedVol ? `${(v.impliedVol * 100).toFixed(0)}%` : '-'}
                        </td>
                        <td className="px-4 py-2 text-right">
                          {v.realizedVol1Y ? `${(v.realizedVol1Y * 100).toFixed(0)}%` : '-'}
                        </td>
                        <td className="px-4 py-2 text-gray-500 text-xs">{v.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Institutional Views */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Institutional Views</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Region</th>
                      <th className="px-4 py-2 text-center">Stance</th>
                      <th className="px-4 py-2 text-left">Sources</th>
                      <th className="px-4 py-2 text-left">Key Drivers</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {marketData.institutionalViews.map((v) => (
                      <tr key={v.region}>
                        <td className="px-4 py-2 font-medium">{v.region}</td>
                        <td className="px-4 py-2 text-center">
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${
                              v.stance === 'overweight'
                                ? 'bg-green-100 text-green-700'
                                : v.stance === 'underweight'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {v.stance}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-gray-500 text-xs">
                          {v.sources.join(', ')}
                        </td>
                        <td className="px-4 py-2 text-gray-500 text-xs">
                          {v.keyDrivers.join(', ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Correlations Matrix */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">
                Correlations
                <span className="ml-2 text-xs text-gray-500">(10-year historical)</span>
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left"></th>
                      {(marketData.correlations?.assets || ['US', 'Europe', 'Japan', 'EM', 'Gold']).map((asset) => (
                        <th key={asset} className="px-3 py-2 text-center text-xs">{asset}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {(() => {
                      const assets = marketData.correlations?.assets || ['US', 'Europe', 'Japan', 'EM', 'Gold'];
                      const defaultMatrix: Record<string, Record<string, number>> = {
                        US:     { US: 1.00, Europe: 0.85, Japan: 0.65, EM: 0.70, Gold: 0.05 },
                        Europe: { US: 0.85, Europe: 1.00, Japan: 0.60, EM: 0.65, Gold: 0.10 },
                        Japan:  { US: 0.65, Europe: 0.60, Japan: 1.00, EM: 0.55, Gold: 0.05 },
                        EM:     { US: 0.70, Europe: 0.65, Japan: 0.55, EM: 1.00, Gold: 0.15 },
                        Gold:   { US: 0.05, Europe: 0.10, Japan: 0.05, EM: 0.15, Gold: 1.00 },
                      };
                      const matrix = marketData.correlations?.matrix;

                      return assets.map((rowAsset, i) => (
                        <tr key={rowAsset}>
                          <td className="px-3 py-2 font-medium text-xs">{rowAsset}</td>
                          {assets.map((colAsset, j) => {
                            const value = matrix ? matrix[i][j] : (defaultMatrix[rowAsset]?.[colAsset] ?? 0);
                            const isLow = value < 0.3;
                            const isHigh = value > 0.7 && i !== j;
                            return (
                              <td
                                key={colAsset}
                                className={`px-3 py-2 text-center text-xs ${
                                  i === j ? 'bg-gray-100 text-gray-400' :
                                  isLow ? 'text-green-600' :
                                  isHigh ? 'text-red-600' : ''
                                }`}
                              >
                                {value.toFixed(2)}
                              </td>
                            );
                          })}
                        </tr>
                      ));
                    })()}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Green = low correlation (good diversifier). Red = high correlation.
              </p>
            </div>

            {/* Rates */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Risk-Free Rate</div>
                <div className="text-xl font-semibold">
                  {(marketData.riskFreeRate * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">EUR/PLN Rate</div>
                <div className="text-xl font-semibold">{marketData.eurPlnRate.toFixed(2)}</div>
              </div>
            </div>

            {/* Data freshness */}
            <div className="text-xs text-gray-400 text-center">
              Data fetched: {new Date(marketData.fetchedAt).toLocaleString()}
            </div>
          </div>
        )}
      </div>

      {marketData && (
        <button onClick={handleContinue} className="btn btn-primary w-full">
          Continue to Results
        </button>
      )}
    </div>
  );
}
