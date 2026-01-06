import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  Portfolio,
  BondPosition,
  CRRAResult,
  MarketData,
  OptimizationResult,
  GapAnalysisRow,
  AllocationRecommendation,
  WorkflowStep,
} from '../types';

interface AppState {
  // Bond state
  bondPosition: BondPosition | null;
  setBondPosition: (bond: BondPosition | null) => void;

  // Portfolio state
  portfolio: Portfolio | null;
  setPortfolio: (portfolio: Portfolio | null) => void;

  // CRRA state
  crra: number | null;
  crraMethod: 'direct' | 'survey' | null;
  crraProfile: CRRAResult['profile'] | null;
  setCrra: (value: number, method: 'direct' | 'survey', profile: CRRAResult['profile']) => void;

  // Market data state
  marketData: MarketData | null;
  marketDataLoading: boolean;
  setMarketData: (data: MarketData | null) => void;
  setMarketDataLoading: (loading: boolean) => void;

  // Optimization results
  optimizationResult: OptimizationResult | null;
  gapAnalysis: GapAnalysisRow[] | null;
  recommendations: AllocationRecommendation[] | null;
  contributionAmount: number;
  setOptimizationResult: (result: OptimizationResult | null) => void;
  setGapAnalysis: (analysis: GapAnalysisRow[] | null) => void;
  setRecommendations: (recs: AllocationRecommendation[] | null) => void;
  setContributionAmount: (amount: number) => void;

  // Workflow state
  completedSteps: WorkflowStep[];
  markStepComplete: (step: WorkflowStep) => void;
  isStepComplete: (step: WorkflowStep) => boolean;

  // Reset
  resetAll: () => void;
}

const initialState = {
  bondPosition: null,
  portfolio: null,
  crra: null,
  crraMethod: null,
  crraProfile: null,
  marketData: null,
  marketDataLoading: false,
  optimizationResult: null,
  gapAnalysis: null,
  recommendations: null,
  contributionAmount: 1000,
  completedSteps: [] as WorkflowStep[],
};

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...initialState,

      setBondPosition: (bondPosition) => set({ bondPosition }),

      setPortfolio: (portfolio) => set({ portfolio }),

      setCrra: (value, method, profile) =>
        set({
          crra: value,
          crraMethod: method,
          crraProfile: profile,
        }),

      setMarketData: (marketData) =>
        set({ marketData, marketDataLoading: false }),

      setMarketDataLoading: (loading) => set({ marketDataLoading: loading }),

      setOptimizationResult: (optimizationResult) => set({ optimizationResult }),

      setGapAnalysis: (gapAnalysis) => set({ gapAnalysis }),

      setRecommendations: (recommendations) => set({ recommendations }),

      setContributionAmount: (contributionAmount) => set({ contributionAmount }),

      markStepComplete: (step) =>
        set((state) => ({
          completedSteps: state.completedSteps.includes(step)
            ? state.completedSteps
            : [...state.completedSteps, step],
        })),

      isStepComplete: (step) => get().completedSteps.includes(step),

      resetAll: () => set(initialState),
    }),
    {
      name: 'merton-portfolio-storage',
      partialize: (state) => ({
        bondPosition: state.bondPosition,
        portfolio: state.portfolio,
        crra: state.crra,
        crraMethod: state.crraMethod,
        crraProfile: state.crraProfile,
        marketData: state.marketData,
        contributionAmount: state.contributionAmount,
        completedSteps: state.completedSteps,
      }),
    }
  )
);
