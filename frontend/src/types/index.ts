// Portfolio types
export interface ETFHolding {
  ticker: string;
  isin?: string;
  name?: string;
  region?: string;  // US, Europe, Japan, EM, Gold
  valueEur: number;
  percentage: number;
  isAccumulating: boolean;
  currencyDenomination: string;
  isUcits: boolean;
  ter: number;
  constraintViolations?: string[];
}

// ETF Metadata from Claude lookup
export interface ETFMetadata {
  ticker: string;
  region: string;
  name?: string;
  isin?: string;
  ter?: number;
  isAccumulating?: boolean;
  description?: string;
}

export interface BondPosition {
  amountPln: number;
  yieldRate: number;
  lockDate: string;
  amountEur?: number;
}

export interface Portfolio {
  holdings: ETFHolding[];
  totalValueEur: number;
  bondPosition?: BondPosition;
}

// CRRA types
export interface CRRASurveyResponses {
  lossThreshold: number;
  riskPercentage: number;
  stockAllocation: number;
  safeChoice: number;
}

export interface RiskProfile {
  riskProfile: string;
  description: string;
  typicalAllocation: string;
  investorType: string;
  percentile: string;
}

export interface CRRAResult {
  crra: number;
  profile: RiskProfile;
}

// Market data types
export interface Valuation {
  region: string;
  cape: number | null;
  forwardPe: number | null;
  dividendYield: number;
  source: string;
  date: string;
}

export interface Volatility {
  asset: string;
  impliedVol: number | null;
  realizedVol1Y: number | null;
  source: string;
}

export interface InstitutionalView {
  region: string;
  stance: 'overweight' | 'neutral' | 'underweight';
  sources: string[];
  keyDrivers: string[];
}

export interface ExpectedReturn {
  region: string;
  return: number;
  rationale: string;
  confidence?: 'high' | 'medium' | 'low';
  isSuspicious?: boolean;
  warningMessage?: string;
}

export interface CorrelationMatrix {
  assets: string[];
  matrix: number[][];
}

export interface MarketData {
  valuations: Valuation[];
  volatility: Volatility[];
  institutionalViews: InstitutionalView[];
  expectedReturns?: ExpectedReturn[];
  correlations?: CorrelationMatrix;
  riskFreeRate: number;
  eurPlnRate: number;
  fetchedAt: string;
  sources: string[];
}

// Optimization types
export interface OptimizationResult {
  optimalWeights: Record<string, number>;
  portfolioStats: {
    return: number;
    volatility: number;
    sharpeRatio: number;
    crraUtility: number;
    riskContribution: Record<string, number>;
    returnConfidenceInterval?: [number, number];
    estimationUncertainty?: 'low' | 'medium' | 'high';
  };
}

export interface GapAnalysisRow {
  ticker: string;
  region?: string;
  currentPct: number;
  targetPct: number;
  gap: number;
  priority: 'high' | 'medium' | 'consider' | 'hold' | 'skip';
  valuationSignal?: 'favorable' | 'neutral' | 'cautious';
  institutionalStance?: 'overweight' | 'neutral' | 'underweight';
}

export interface AllocationRecommendation {
  ticker: string;
  isin?: string;
  amountEur: number;
  percentageOfContribution: number;
  rationale: string;
}

// Rebalancing types
export interface SellRecommendation {
  ticker: string;
  currentPct: number;
  targetPct: number;
  excessPct: number;
  rationale: string;
}

export interface RebalanceCheck {
  isRebalanceRecommended: boolean;
  maxDeviation: number;
  overweightPositions: SellRecommendation[];
  underweightPositions: string[];
  taxNote: string;
}

// Workflow step type
export type WorkflowStep = 'bonds' | 'portfolio' | 'risk-profile' | 'market-data' | 'results';

export const WORKFLOW_STEPS: { id: WorkflowStep; label: string; path: string }[] = [
  { id: 'bonds', label: 'Bonds', path: '/bonds' },
  { id: 'portfolio', label: 'Portfolio', path: '/portfolio' },
  { id: 'risk-profile', label: 'Risk Profile', path: '/risk-profile' },
  { id: 'market-data', label: 'Market Data', path: '/market-data' },
  { id: 'results', label: 'Results', path: '/results' },
];
