import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store';
import type { UserStance } from '../store';
import type { MarketData } from '../types';

// Regions the user can express a view on. Must match the backend region names
// emitted in market_data.txt / expected_returns.
const VIEW_REGIONS = ['US', 'Europe', 'Japan', 'EM', 'Pacific', 'Gold'] as const;

const STANCE_OPTIONS: { value: UserStance | null; label: string }[] = [
  { value: null, label: 'No opinion' },
  { value: 'overweight', label: 'Overweight' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'underweight', label: 'Underweight' },
];

export default function MarketDataPage() {
  const navigate = useNavigate();
  const {
    marketData,
    setMarketData,
    markStepComplete,
    setMarketDataLoading,
    marketDataLoading,
    userViews,
    setUserView,
  } = useAppStore();
  const [error, setError] = useState<string | null>(null);
  const [rawData, setRawData] = useState<unknown>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [progress, setProgress] = useState<{ stage: string; detail: string; at: string }[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fmtElapsed = (s: number) =>
    `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  const handleFetchMarketData = async () => {
    setError(null);
    setProgress([]);
    setElapsed(0);
    setMarketDataLoading(true);

    const start = Date.now();
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(
      () => setElapsed(Math.floor((Date.now() - start) / 1000)),
      1000,
    );

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch('/api/v1/market-data/gather/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          force_refresh: true,
          // Only send regions the user explicitly took a stance on.
          user_views: Object.keys(userViews).length > 0 ? userViews : undefined,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Failed to start fetch (HTTP ${response.status})`);
      }

      // Read the Server-Sent Events stream: each event is a "data: <json>" line
      // separated by a blank line. Accumulate status events into `progress`,
      // and capture the final `result` payload.
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let data: any = null;

      streamLoop: while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split('\n\n');
        buffer = chunks.pop() ?? '';
        for (const chunk of chunks) {
          const line = chunk.trim();
          if (!line.startsWith('data:')) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          const evt = JSON.parse(payload) as {
            type: string;
            stage?: string;
            detail?: string;
            data?: Record<string, unknown>;
          };
          if (evt.type === 'status') {
            const at = new Date().toLocaleTimeString([], { hour12: false });
            setProgress((prev) => {
              const last = prev[prev.length - 1];
              if (last && last.stage === evt.stage && last.detail === evt.detail) return prev;
              return [...prev, { stage: evt.stage ?? '', detail: evt.detail ?? '', at }];
            });
          } else if (evt.type === 'error') {
            throw new Error(evt.detail || 'Fetch failed');
          } else if (evt.type === 'result') {
            data = evt.data ?? null;
            break streamLoop;
          }
        }
      }

      if (!data) throw new Error('No data received from server');
      setRawData(data);

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
          confidence: v.confidence as 'high' | 'medium' | 'low' | undefined,
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
        bundYield10y: data.bund_yield_10y,
        eurPlnRate: data.eur_pln_rate,
        fetchedAt: data.fetched_at,
        sources: data.sources,
      };

      setMarketData(marketData);
      markStepComplete('market-data');
    } catch (err) {
      // A user-triggered abort isn't a real error — just leave a soft note.
      if (err instanceof DOMException && err.name === 'AbortError') {
        setProgress([]);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to fetch market data');
      }
    } finally {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      abortRef.current = null;
      setMarketDataLoading(false);
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
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

      {/* Your views — blended with institutional views before optimization */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900">Your Views (optional)</h3>
        <p className="mt-1 mb-4 text-sm text-gray-500">
          Express your own stance per region. Your view is blended with the
          institutional/AI consensus by confidence before expected returns are
          computed. Leave as <span className="font-medium">No opinion</span> to
          rely entirely on the research.
        </p>
        <div className="space-y-2">
          {VIEW_REGIONS.map((region) => {
            const selected = (userViews[region] ?? null) as UserStance | null;
            return (
              <div key={region} className="flex items-center gap-3">
                <div className="w-20 text-sm font-medium text-gray-700">{region}</div>
                <div className="flex flex-wrap gap-1">
                  {STANCE_OPTIONS.map((opt) => {
                    const isActive = selected === opt.value;
                    const activeClass =
                      opt.value === 'overweight'
                        ? 'bg-green-600 text-white border-green-600'
                        : opt.value === 'underweight'
                        ? 'bg-red-600 text-white border-red-600'
                        : opt.value === 'neutral'
                        ? 'bg-gray-600 text-white border-gray-600'
                        : 'bg-gray-200 text-gray-700 border-gray-300';
                    return (
                      <button
                        key={opt.label}
                        type="button"
                        onClick={() => setUserView(region, opt.value)}
                        className={`px-3 py-1 text-xs rounded border transition-colors ${
                          isActive
                            ? activeClass
                            : 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'
                        }`}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

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
              'Fetch Data'
            )}
          </button>
        </div>

        {marketDataLoading && (
          <div className="py-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="animate-spin w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full"></span>
              <span className="font-medium text-gray-700">Live from Claude</span>
              <span className="ml-auto text-xs text-gray-400 tabular-nums">
                elapsed {fmtElapsed(elapsed)}
              </span>
            </div>
            <ul className="space-y-1.5 text-sm">
              {progress.map((p, i) => (
                <li key={i} className="flex items-start gap-2 text-gray-600">
                  <span className="text-gray-400 text-xs tabular-nums mt-0.5">{p.at}</span>
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>{p.detail}</span>
                </li>
              ))}
              <li className="flex items-center gap-2 text-gray-400">
                <span className="animate-pulse">⟳</span>
                <span>working…</span>
              </li>
            </ul>
            <div className="flex items-center gap-3 mt-4">
              <button
                onClick={handleCancel}
                className="btn btn-secondary text-sm"
              >
                Cancel
              </button>
              <p className="text-xs text-gray-400">
                Opus 4.8 with web search &amp; reasoning — this usually takes 1–3 min.
              </p>
            </div>
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
                      <th className="px-4 py-2 text-center">Conf</th>
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
                        <td className="px-4 py-2 text-center">
                          <span
                            className={`px-2 py-1 rounded text-xs ${
                              v.confidence === 'high'
                                ? 'bg-blue-50 text-blue-600'
                                : v.confidence === 'medium'
                                ? 'bg-gray-50 text-gray-500'
                                : 'text-gray-400'
                            }`}
                          >
                            {v.confidence ?? 'low'}
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
                      {(marketData.correlations?.assets || ['US', 'Europe', 'Japan', 'EM', 'Pacific', 'Gold']).map((asset) => (
                        <th key={asset} className="px-3 py-2 text-center text-xs">{asset}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {(() => {
                      const assets = marketData.correlations?.assets || ['US', 'Europe', 'Japan', 'EM', 'Pacific', 'Gold'];
                      const defaultMatrix: Record<string, Record<string, number>> = {
                        US:      { US: 1.00, Europe: 0.85, Japan: 0.65, EM: 0.70, Pacific: 0.70, Gold: 0.05 },
                        Europe:  { US: 0.85, Europe: 1.00, Japan: 0.60, EM: 0.65, Pacific: 0.70, Gold: 0.10 },
                        Japan:   { US: 0.65, Europe: 0.60, Japan: 1.00, EM: 0.55, Pacific: 0.65, Gold: 0.05 },
                        EM:      { US: 0.70, Europe: 0.65, Japan: 0.55, EM: 1.00, Pacific: 0.70, Gold: 0.15 },
                        Pacific: { US: 0.70, Europe: 0.70, Japan: 0.65, EM: 0.70, Pacific: 1.00, Gold: 0.10 },
                        Gold:    { US: 0.05, Europe: 0.10, Japan: 0.05, EM: 0.15, Pacific: 0.10, Gold: 1.00 },
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
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">ECB Rate (risk-free)</div>
                <div className="text-xl font-semibold">
                  {(marketData.riskFreeRate * 100).toFixed(2)}%
                </div>
              </div>
              {marketData.bundYield10y != null && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-500">German 10Y Bund</div>
                  <div className="text-xl font-semibold">
                    {(marketData.bundYield10y * 100).toFixed(2)}%
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Real yield: {((marketData.bundYield10y - 0.02) * 100).toFixed(2)}%
                  </div>
                </div>
              )}
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">EUR/PLN</div>
                <div className="text-xl font-semibold">{marketData.eurPlnRate.toFixed(4)}</div>
              </div>
            </div>

            {/* Data freshness */}
            <div className="text-xs text-gray-400 text-center">
              Data fetched: {new Date(marketData.fetchedAt).toLocaleString()}
            </div>

            {/* Raw JSON */}
            {rawData != null && (
              <div>
                <button
                  onClick={() => setShowRaw((v) => !v)}
                  className="text-xs text-blue-500 hover:underline"
                >
                  {showRaw ? 'Hide raw response' : 'Show raw response'}
                </button>
                {showRaw && (
                  <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs overflow-auto max-h-96">
                    {JSON.stringify(rawData, null, 2)}
                  </pre>
                )}
              </div>
            )}
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
