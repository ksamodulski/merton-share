import type { RiskProfile } from '../../types';

interface Props {
  crra: number;
  profile: RiskProfile;
}

export default function RiskProfileDisplay({ crra, profile }: Props) {
  const getColorClass = (riskProfile: string) => {
    switch (riskProfile) {
      case 'Very Aggressive':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'Aggressive':
        return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'Moderate':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'Conservative':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'Very Conservative':
        return 'bg-green-100 text-green-700 border-green-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="text-center">
          <div className="text-4xl font-bold text-primary-600">{crra.toFixed(1)}</div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">CRRA</div>
        </div>
        <div className={`px-4 py-2 rounded-lg border ${getColorClass(profile.riskProfile)}`}>
          <div className="font-semibold">{profile.riskProfile}</div>
          <div className="text-sm opacity-80">{profile.investorType}</div>
        </div>
      </div>

      <p className="text-gray-600">{profile.description}</p>

      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">
            Typical Allocation
          </div>
          <div className="font-medium text-gray-900">{profile.typicalAllocation}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">
            Market Context
          </div>
          <div className="font-medium text-gray-900">{profile.percentile}</div>
        </div>
      </div>

      {/* Visual scale */}
      <div className="pt-4">
        <div className="text-xs text-gray-500 mb-2">Risk Scale</div>
        <div className="relative h-3 bg-gradient-to-r from-red-400 via-yellow-400 to-green-400 rounded-full">
          <div
            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-gray-800 rounded-full shadow"
            style={{ left: `${((crra - 1) / 9) * 100}%`, transform: 'translate(-50%, -50%)' }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>Aggressive (1)</span>
          <span>Conservative (10)</span>
        </div>
      </div>
    </div>
  );
}
