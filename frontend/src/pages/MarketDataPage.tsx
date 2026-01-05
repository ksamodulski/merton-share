import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store';
import { marketDataApi } from '../services/api';

// Default values from step2 prompt
const DEFAULT_MARKET_DATA = {
  valuations: [
    { region: 'US', cape: 35, forwardPe: 21, dividendYield: 0.013 },
    { region: 'Europe', cape: 15, forwardPe: 13, dividendYield: 0.028 },
    { region: 'Japan', cape: 22, forwardPe: 15, dividendYield: 0.020 },
    { region: 'EM', cape: 12, forwardPe: 12, dividendYield: 0.025 },
  ],
  volatility: [
    { asset: 'US', impliedVol: 0.16, realizedVol1Y: 0.15 },
    { asset: 'Europe', impliedVol: 0.18, realizedVol1Y: 0.17 },
    { asset: 'Japan', impliedVol: 0.20, realizedVol1Y: 0.19 },
    { asset: 'EM', impliedVol: 0.22, realizedVol1Y: 0.21 },
    { asset: 'Gold', impliedVol: 0.15, realizedVol1Y: 0.14 },
  ],
  riskFreeRate: 0.025,
  eurPlnRate: 4.30,
};

export default function MarketDataPage() {
  const navigate = useNavigate();
  const { marketData, setMarketData, markStepComplete, setMarketDataLoading, marketDataLoading } = useAppStore();
  const [useDefaults, setUseDefaults] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleFetchMarketData = async () => {
    setError(null);
    setMarketDataLoading(true);
    try {
      // Try to fetch from API
      await marketDataApi.gather(true);
    } catch (err) {
      // API not implemented yet, use defaults
      setError('Live market data not available yet. Using default values.');
    }
    setMarketDataLoading(false);
  };

  const handleUseDefaults = () => {
    setMarketData({
      valuations: DEFAULT_MARKET_DATA.valuations.map((v) => ({
        region: v.region,
        cape: v.cape,
        forwardPe: v.forwardPe,
        dividendYield: v.dividendYield,
        source: 'Default values',
        date: new Date().toISOString().split('T')[0],
      })),
      volatility: DEFAULT_MARKET_DATA.volatility.map((v) => ({
        asset: v.asset,
        impliedVol: v.impliedVol,
        realizedVol1Y: v.realizedVol1Y,
        source: 'Default values',
      })),
      institutionalViews: [
        { region: 'US', stance: 'neutral', sources: ['Default'], keyDrivers: [] },
        { region: 'Europe', stance: 'overweight', sources: ['Default'], keyDrivers: [] },
        { region: 'Japan', stance: 'overweight', sources: ['Default'], keyDrivers: [] },
        { region: 'EM', stance: 'neutral', sources: ['Default'], keyDrivers: [] },
        { region: 'Gold', stance: 'neutral', sources: ['Default'], keyDrivers: [] },
      ],
      riskFreeRate: DEFAULT_MARKET_DATA.riskFreeRate,
      eurPlnRate: DEFAULT_MARKET_DATA.eurPlnRate,
      fetchedAt: new Date().toISOString(),
      sources: ['Default values from step2 prompt'],
    });
    markStepComplete('market-data');
  };

  const handleContinue = () => {
    navigate('/results');
  };

  const data = marketData || (useDefaults ? {
    valuations: DEFAULT_MARKET_DATA.valuations,
    volatility: DEFAULT_MARKET_DATA.volatility,
    riskFreeRate: DEFAULT_MARKET_DATA.riskFreeRate,
    eurPlnRate: DEFAULT_MARKET_DATA.eurPlnRate,
  } : null);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Market Data</h2>
        <p className="mt-1 text-gray-500">
          Current market valuations, volatility, and institutional views.
          Live data fetching will be available in Phase 3.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm">
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
            {marketDataLoading ? 'Fetching...' : 'Fetch Live Data'}
          </button>
          <button onClick={handleUseDefaults} className="btn btn-secondary">
            Use Default Values
          </button>
        </div>

        {data && (
          <div className="space-y-6">
            {/* Valuations Table */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Valuations</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Region</th>
                      <th className="px-4 py-2 text-right">CAPE</th>
                      <th className="px-4 py-2 text-right">Fwd P/E</th>
                      <th className="px-4 py-2 text-right">Div Yield</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.valuations.map((v) => (
                      <tr key={v.region}>
                        <td className="px-4 py-2 font-medium">{v.region}</td>
                        <td className="px-4 py-2 text-right">{v.cape ?? '-'}</td>
                        <td className="px-4 py-2 text-right">{v.forwardPe ?? '-'}</td>
                        <td className="px-4 py-2 text-right">
                          {(v.dividendYield * 100).toFixed(1)}%
                        </td>
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
                      <th className="px-4 py-2 text-right">Implied Vol</th>
                      <th className="px-4 py-2 text-right">1Y Realized</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.volatility.map((v) => (
                      <tr key={v.asset}>
                        <td className="px-4 py-2 font-medium">{v.asset}</td>
                        <td className="px-4 py-2 text-right">
                          {v.impliedVol ? `${(v.impliedVol * 100).toFixed(0)}%` : '-'}
                        </td>
                        <td className="px-4 py-2 text-right">
                          {v.realizedVol1Y ? `${(v.realizedVol1Y * 100).toFixed(0)}%` : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Rates */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Risk-Free Rate</div>
                <div className="text-xl font-semibold">
                  {(data.riskFreeRate * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">EUR/PLN Rate</div>
                <div className="text-xl font-semibold">{data.eurPlnRate.toFixed(2)}</div>
              </div>
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
