import { useEffect, useState } from 'react';
import { useAppStore } from '../store';
import { optimizeApi } from '../services/api';
import type { RebalanceCheck } from '../types';

export default function ResultsPage() {
  const {
    portfolio,
    bondPosition,
    crra,
    marketData,
    contributionAmount,
    setContributionAmount,
    optimizationResult,
    setOptimizationResult,
    gapAnalysis,
    setGapAnalysis,
    recommendations,
    setRecommendations,
    markStepComplete,
  } = useAppStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rebalanceCheck, setRebalanceCheck] = useState<RebalanceCheck | null>(null);

  const runOptimization = async () => {
    if (!portfolio || !crra || !marketData) {
      setError('Missing required data. Please complete all previous steps.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Build optimization request from market data
      const regions = ['US', 'Europe', 'Japan', 'EM', 'Gold'];

      // Use expected returns from Claude if available, otherwise calculate from CAPE
      const expectedReturns = regions.map((region) => {
        // First try Claude's expected returns
        const expectedReturn = marketData.expectedReturns?.find((r) => r.region === region);
        if (expectedReturn) {
          return expectedReturn.return;
        }
        // Fallback: calculate from CAPE + dividend yield
        const valuation = marketData.valuations.find((v) => v.region === region);
        if (!valuation) return 0.05;
        const cape = valuation.cape || 20;
        return 1 / cape + valuation.dividendYield;
      });

      // Get volatilities from market data
      const volatilities = regions.map((region) => {
        const vol = marketData.volatility.find((v) => v.asset === region);
        return vol?.realizedVol1Y || vol?.impliedVol || 0.18;
      });

      // Use correlation matrix from Claude if available, otherwise use defaults
      let correlationMatrix: number[][];
      if (marketData.correlations?.matrix) {
        // Reorder to match our regions order if needed
        const claudeAssets = marketData.correlations.assets;
        correlationMatrix = regions.map((r1, i) =>
          regions.map((r2, j) => {
            if (i === j) return 1;
            const idx1 = claudeAssets.indexOf(r1);
            const idx2 = claudeAssets.indexOf(r2);
            if (idx1 >= 0 && idx2 >= 0) {
              return marketData.correlations!.matrix[idx1][idx2];
            }
            // Default correlations
            if (r1 === 'Gold' || r2 === 'Gold') return 0.1;
            return 0.6;
          })
        );
      } else {
        // Default correlation matrix
        const n = regions.length;
        correlationMatrix = Array(n).fill(null).map((_, i) =>
          Array(n).fill(null).map((_, j) => {
            if (i === j) return 1;
            if (regions[i] === 'Gold' || regions[j] === 'Gold') return 0.1;
            return 0.6;
          })
        );
      }

      const result = await optimizeApi.optimize({
        assets: regions,
        expected_returns: expectedReturns,
        volatilities,
        correlation_matrix: correlationMatrix,
        crra,
      });

      setOptimizationResult({
        optimalWeights: result.optimal_weights,
        portfolioStats: {
          return: result.portfolio_stats.return,
          volatility: result.portfolio_stats.volatility,
          sharpeRatio: result.portfolio_stats.sharpe_ratio,
          crraUtility: result.portfolio_stats.crra_utility,
          riskContribution: result.portfolio_stats.risk_contribution,
        },
      });

      // Calculate current allocation using region from ETF metadata
      const currentAllocation: Record<string, number> = {};
      portfolio.holdings.forEach((h) => {
        // Use region from ETF metadata if available
        const region = h.region || guessRegionFromTicker(h.ticker);
        currentAllocation[region] = (currentAllocation[region] || 0) + h.percentage;
      });

      // Get valuation signals for gap analysis
      const valuationSignals: Record<string, string> = {};
      marketData.valuations.forEach((v) => {
        // Determine signal based on CAPE thresholds
        const cape = v.cape;
        if (v.region === 'US') {
          valuationSignals[v.region] = cape && cape > 35 ? 'cautious' : cape && cape < 25 ? 'favorable' : 'neutral';
        } else if (v.region === 'Europe') {
          valuationSignals[v.region] = v.forwardPe && v.forwardPe > 16 ? 'cautious' : v.forwardPe && v.forwardPe < 14 ? 'favorable' : 'neutral';
        } else {
          valuationSignals[v.region] = 'neutral';
        }
      });

      // Get institutional stances
      const institutionalStances: Record<string, string> = {};
      marketData.institutionalViews.forEach((v) => {
        institutionalStances[v.region] = v.stance;
      });

      const gapResult = await optimizeApi.gapAnalysis({
        current_allocation: currentAllocation,
        target_allocation: result.optimal_weights,
        valuations: valuationSignals,
        institutional_stances: institutionalStances,
      });

      setGapAnalysis(
        gapResult.rows.map((r) => ({
          ticker: r.ticker,
          currentPct: r.current_pct,
          targetPct: r.target_pct,
          gap: r.gap,
          priority: r.priority as 'high' | 'medium' | 'consider' | 'hold' | 'skip',
          valuationSignal: r.valuation_signal as 'favorable' | 'neutral' | 'cautious' | undefined,
          institutionalStance: r.institutional_stance as 'overweight' | 'neutral' | 'underweight' | undefined,
        }))
      );

      // Check for rebalancing recommendations
      try {
        const rebalanceResult = await fetch('/api/v1/optimize/rebalance-check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            current_allocation: currentAllocation,
            target_allocation: result.optimal_weights,
            rebalance_threshold: 5.0,
          }),
        });
        if (rebalanceResult.ok) {
          const rebalanceData = await rebalanceResult.json();
          setRebalanceCheck({
            isRebalanceRecommended: rebalanceData.is_rebalance_recommended,
            maxDeviation: rebalanceData.max_deviation,
            overweightPositions: rebalanceData.overweight_positions.map((p: Record<string, unknown>) => ({
              ticker: p.ticker,
              currentPct: p.current_pct,
              targetPct: p.target_pct,
              excessPct: p.excess_pct,
              rationale: p.rationale,
            })),
            underweightPositions: rebalanceData.underweight_positions,
            taxNote: rebalanceData.tax_note,
          });
        }
      } catch (err) {
        console.warn('Rebalance check failed:', err);
      }

      // Get allocation recommendations
      if (contributionAmount > 0 && portfolio) {
        const allocResult = await optimizeApi.allocate({
          contribution_amount: contributionAmount,
          current_portfolio_value: portfolio.totalValueEur,
          gap_analysis: gapResult,
          min_allocation: 500,
        });

        setRecommendations(
          allocResult.recommendations.map((r) => ({
            ticker: r.ticker,
            amountEur: r.amount_eur,
            percentageOfContribution: r.percentage_of_contribution,
            rationale: r.rationale,
          }))
        );
      }

      markStepComplete('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Optimization failed');
    } finally {
      setLoading(false);
    }
  };

  // Fallback function to guess region from ticker name
  const guessRegionFromTicker = (ticker: string): string => {
    const t = ticker.toUpperCase();
    if (t.includes('GLD') || t === '4GLD') return 'Gold';
    if (t.includes('EM') || t.includes('IEMA')) return 'EM';
    if (t.includes('JP') || t.includes('IJPA')) return 'Japan';
    if (t.includes('EUR') || t.includes('MEUD') || t.includes('EUNK')) return 'Europe';
    return 'US';
  };

  useEffect(() => {
    if (portfolio && crra && marketData && !optimizationResult) {
      runOptimization();
    }
  }, [portfolio, crra, marketData]);

  if (!portfolio || !crra || !marketData) {
    return (
      <div className="card text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Complete Previous Steps
        </h2>
        <p className="text-gray-500">
          Please complete the portfolio, risk profile, and market data steps first.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Optimization Results</h2>
        <p className="mt-1 text-gray-500">
          Merton optimal allocation based on your inputs.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="card text-center py-12">
          <div className="animate-spin w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-500">Running optimization...</p>
        </div>
      ) : optimizationResult ? (
        <>
          {/* Optimal Weights */}
          <div className="card">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Optimal Weights</h3>
            <div className="space-y-3">
              {Object.entries(optimizationResult.optimalWeights)
                .sort(([, a], [, b]) => b - a)
                .map(([asset, weight]) => (
                  <div key={asset} className="flex items-center gap-3">
                    <span className="w-20 text-sm font-medium">{asset}</span>
                    <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 rounded-full"
                        style={{ width: `${weight}%` }}
                      />
                    </div>
                    <span className="w-16 text-right text-sm font-medium">
                      {weight.toFixed(1)}%
                    </span>
                  </div>
                ))}
            </div>
          </div>

          {/* Portfolio Stats */}
          <div className="card">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Portfolio Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Expected Return</div>
                <div className="text-xl font-semibold text-green-600">
                  {optimizationResult.portfolioStats.return.toFixed(1)}%
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Volatility</div>
                <div className="text-xl font-semibold text-amber-600">
                  {optimizationResult.portfolioStats.volatility.toFixed(1)}%
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Sharpe Ratio</div>
                <div className="text-xl font-semibold">
                  {optimizationResult.portfolioStats.sharpeRatio.toFixed(2)}
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">CRRA Utility</div>
                <div className="text-xl font-semibold">
                  {optimizationResult.portfolioStats.crraUtility.toFixed(3)}
                </div>
              </div>
            </div>
          </div>

          {/* Gap Analysis */}
          {gapAnalysis && (
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Gap Analysis</h3>
              <p className="text-sm text-gray-500 mb-4">
                Positive gap = underweight (buy opportunity). Negative gap = overweight (consider rebalancing).
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Region</th>
                      <th className="px-4 py-2 text-right">Current</th>
                      <th className="px-4 py-2 text-right">Target</th>
                      <th className="px-4 py-2 text-right">Gap</th>
                      <th className="px-4 py-2 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {gapAnalysis.map((row) => (
                      <tr key={row.ticker}>
                        <td className="px-4 py-2 font-medium">{row.ticker}</td>
                        <td className="px-4 py-2 text-right">{row.currentPct.toFixed(1)}%</td>
                        <td className="px-4 py-2 text-right">{row.targetPct.toFixed(1)}%</td>
                        <td
                          className={`px-4 py-2 text-right font-medium ${
                            row.gap > 0 ? 'text-green-600' : row.gap < -3 ? 'text-red-600' : 'text-gray-600'
                          }`}
                        >
                          {row.gap > 0 ? '+' : ''}
                          {row.gap.toFixed(1)}%
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${
                              row.priority === 'high'
                                ? 'bg-green-100 text-green-700'
                                : row.priority === 'medium'
                                ? 'bg-blue-100 text-blue-700'
                                : row.priority === 'consider'
                                ? 'bg-yellow-100 text-yellow-700'
                                : row.priority === 'hold'
                                ? 'bg-gray-100 text-gray-700'
                                : 'bg-red-100 text-red-700'
                            }`}
                          >
                            {row.priority === 'high' ? 'BUY' :
                             row.priority === 'medium' ? 'accumulate' :
                             row.priority === 'consider' ? 'consider' :
                             row.priority === 'hold' ? 'hold' : 'skip'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Rebalancing Check */}
          {rebalanceCheck && rebalanceCheck.isRebalanceRecommended && (
            <div className="card border-amber-200 bg-amber-50">
              <h3 className="text-lg font-medium text-amber-900 mb-4">
                Quarterly Rebalancing Check
              </h3>
              <p className="text-amber-700 mb-4">
                Some positions have drifted significantly from target (max deviation: {rebalanceCheck.maxDeviation.toFixed(1)}%).
                Consider rebalancing when convenient.
              </p>
              {rebalanceCheck.overweightPositions.length > 0 && (
                <div className="space-y-2 mb-4">
                  <p className="text-sm font-medium text-amber-800">Overweight positions to consider reducing:</p>
                  {rebalanceCheck.overweightPositions.map((pos) => (
                    <div key={pos.ticker} className="p-3 bg-white rounded-lg border border-amber-200">
                      <span className="font-medium">{pos.ticker}</span>: {pos.excessPct.toFixed(1)}% above target
                    </div>
                  ))}
                </div>
              )}
              <p className="text-xs text-amber-600">{rebalanceCheck.taxNote}</p>
            </div>
          )}

          {/* Contribution Allocation */}
          <div className="card">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Monthly Contribution Allocation
            </h3>
            <div className="mb-4">
              <label className="label">Contribution Amount (EUR)</label>
              <input
                type="number"
                value={contributionAmount}
                onChange={(e) => setContributionAmount(parseFloat(e.target.value) || 0)}
                className="input w-48"
                min="0"
                step="100"
              />
              <button
                onClick={runOptimization}
                className="ml-3 btn btn-secondary"
                disabled={loading}
              >
                Recalculate
              </button>
            </div>

            {recommendations && recommendations.length > 0 ? (
              <div className="space-y-3">
                {recommendations.map((rec) => (
                  <div
                    key={rec.ticker}
                    className="flex items-center justify-between p-4 bg-primary-50 rounded-lg"
                  >
                    <div>
                      <div className="font-semibold text-primary-900">{rec.ticker}</div>
                      <div className="text-sm text-primary-700">{rec.rationale}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold text-primary-600">
                        €{rec.amountEur.toLocaleString()}
                      </div>
                      <div className="text-sm text-primary-500">
                        {rec.percentageOfContribution.toFixed(0)}% of contribution
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">
                {contributionAmount > 0
                  ? 'Portfolio is well-balanced. No specific allocation recommendations.'
                  : 'Enter a contribution amount to see allocation recommendations.'}
              </p>
            )}
          </div>
        </>
      ) : (
        <button onClick={runOptimization} className="btn btn-primary w-full">
          Run Optimization
        </button>
      )}
    </div>
  );
}
