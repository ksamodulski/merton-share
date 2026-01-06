const API_BASE = '/api/v1';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }

  return response.json();
}

// CRRA API
export const crraApi = {
  calculate: (responses: {
    loss_threshold: number;
    risk_percentage: number;
    stock_allocation: number;
    safe_choice: number;
  }) =>
    request<{ crra: number; profile: Record<string, string> }>('/crra/calculate', {
      method: 'POST',
      body: JSON.stringify(responses),
    }),

  interpret: (crra: number) =>
    request<{ crra: number; profile: Record<string, string> }>('/crra/interpret', {
      method: 'POST',
      body: JSON.stringify({ crra }),
    }),

  getScale: () =>
    request<{ scale: Array<{ range: string; profile: string; typical_investor: string }> }>(
      '/crra/scale'
    ),
};

// Optimization API
export const optimizeApi = {
  optimize: (data: {
    assets: string[];
    expected_returns: number[];
    volatilities: number[];
    correlation_matrix: number[][];
    crra: number;
  }) =>
    request<{
      optimal_weights: Record<string, number>;
      portfolio_stats: {
        return: number;
        volatility: number;
        sharpe_ratio: number;
        crra_utility: number;
        risk_contribution: Record<string, number>;
      };
    }>('/optimize', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  gapAnalysis: (data: {
    current_allocation: Record<string, number>;
    target_allocation: Record<string, number>;
    valuations?: Record<string, string>;
    institutional_stances?: Record<string, string>;
  }) =>
    request<{
      rows: Array<{
        ticker: string;
        current_pct: number;
        target_pct: number;
        gap: number;
        priority: string;
        valuation_signal?: string;
        institutional_stance?: string;
      }>;
      high_priority: string[];
      medium_priority: string[];
    }>('/optimize/gap-analysis', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  allocate: (data: {
    contribution_amount: number;
    current_portfolio_value: number;
    gap_analysis: {
      rows: Array<{
        ticker: string;
        current_pct: number;
        target_pct: number;
        gap: number;
        priority: string;
      }>;
      high_priority: string[];
      medium_priority: string[];
    };
    min_allocation?: number;
  }) =>
    request<{
      total_contribution: number;
      recommendations: Array<{
        ticker: string;
        amount_eur: number;
        percentage_of_contribution: number;
        rationale: string;
      }>;
      unallocated: number;
      post_allocation_preview: Array<{
        ticker: string;
        current_eur: number;
        current_pct: number;
        amount_added: number;
        new_eur: number;
        new_pct: number;
        pct_change: number;
        target_pct: number;
        gap_after: number;
      }>;
    }>('/optimize/allocate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// Portfolio API
export const portfolioApi = {
  validate: (data: {
    holdings: Array<{
      ticker: string;
      value_eur: number;
      percentage: number;
      is_accumulating: boolean;
      currency_denomination: string;
      is_ucits: boolean;
      ter: number;
    }>;
    bond_position?: {
      amount_pln: number;
      yield_rate: number;
      lock_date: string;
    };
  }) =>
    request('/portfolio', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  convertBonds: (amountPln: number, eurPlnRate: number) =>
    request<{ amount_pln: number; amount_eur: number; eur_pln_rate: number }>(
      `/portfolio/bonds/convert?amount_pln=${amountPln}&eur_pln_rate=${eurPlnRate}`,
      { method: 'POST' }
    ),
};

// Market Data API
export const marketDataApi = {
  gather: (forceRefresh = false) =>
    request('/market-data/gather', {
      method: 'POST',
      body: JSON.stringify({ force_refresh: forceRefresh }),
    }),

  getCached: () => request<{ cached: boolean; data?: unknown; age_hours?: number }>('/market-data/cached'),

  getDefaults: () =>
    request<{
      volatilities: Record<string, number>;
      dividend_yields: Record<string, number>;
      thresholds: Array<{
        region: string;
        cautious_cape?: number;
        cautious_pe?: number;
        favorable_cape?: number;
        favorable_pe?: number;
      }>;
      default_risk_free_rate: number;
    }>('/market-data/defaults'),
};

export { ApiError };
