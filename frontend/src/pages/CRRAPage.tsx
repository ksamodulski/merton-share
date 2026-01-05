import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store';
import { crraApi } from '../services/api';
import CRRADirectInput from '../components/crra/CRRADirectInput';
import CRRAQuestionnaire from '../components/crra/CRRAQuestionnaire';
import RiskProfileDisplay from '../components/crra/RiskProfileDisplay';

type InputMethod = 'direct' | 'survey';

export default function CRRAPage() {
  const navigate = useNavigate();
  const { crra, crraProfile, setCrra, markStepComplete } = useAppStore();
  const [method, setMethod] = useState<InputMethod>(crra ? 'direct' : 'survey');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDirectSubmit = async (value: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await crraApi.interpret(value);
      setCrra(result.crra, 'direct', {
        riskProfile: result.profile.risk_profile,
        description: result.profile.description,
        typicalAllocation: result.profile.typical_allocation,
        investorType: result.profile.investor_type,
        percentile: result.profile.percentile,
      });
      markStepComplete('risk-profile');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to interpret CRRA');
    } finally {
      setLoading(false);
    }
  };

  const handleSurveySubmit = async (responses: {
    lossThreshold: number;
    riskPercentage: number;
    stockAllocation: number;
    safeChoice: number;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const result = await crraApi.calculate({
        loss_threshold: responses.lossThreshold,
        risk_percentage: responses.riskPercentage,
        stock_allocation: responses.stockAllocation,
        safe_choice: responses.safeChoice,
      });
      setCrra(result.crra, 'survey', {
        riskProfile: result.profile.risk_profile,
        description: result.profile.description,
        typicalAllocation: result.profile.typical_allocation,
        investorType: result.profile.investor_type,
        percentile: result.profile.percentile,
      });
      markStepComplete('risk-profile');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate CRRA');
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = () => {
    navigate('/market-data');
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Risk Profile</h2>
        <p className="mt-1 text-gray-500">
          Determine your risk tolerance (CRRA) to optimize your portfolio allocation.
        </p>
      </div>

      {/* Method selector */}
      <div className="card">
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setMethod('direct')}
            className={`flex-1 py-3 px-4 rounded-lg border-2 transition-colors ${
              method === 'direct'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="font-medium">Direct Input</div>
            <div className="text-sm text-gray-500">I know my CRRA value</div>
          </button>
          <button
            onClick={() => setMethod('survey')}
            className={`flex-1 py-3 px-4 rounded-lg border-2 transition-colors ${
              method === 'survey'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="font-medium">Questionnaire</div>
            <div className="text-sm text-gray-500">Help me determine it</div>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {method === 'direct' ? (
          <CRRADirectInput
            initialValue={crra ?? 3}
            onSubmit={handleDirectSubmit}
            loading={loading}
          />
        ) : (
          <CRRAQuestionnaire onSubmit={handleSurveySubmit} loading={loading} />
        )}
      </div>

      {/* Results */}
      {crra && crraProfile && (
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Your Risk Profile</h3>
          <RiskProfileDisplay crra={crra} profile={crraProfile} />
          <div className="mt-6 flex justify-end">
            <button onClick={handleContinue} className="btn btn-primary">
              Continue to Market Data
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
