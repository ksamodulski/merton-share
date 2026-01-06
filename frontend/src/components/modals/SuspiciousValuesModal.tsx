import { useState } from 'react';
import type { ExpectedReturn } from '../../types';

interface SuspiciousValueItem {
  region: string;
  value: number;
  warning: string;
  rationale: string;
}

interface Props {
  suspiciousReturns: ExpectedReturn[];
  onConfirm: () => void;
  onReject: () => void;
  onOverride: (overrides: Record<string, number>) => void;
  isOpen: boolean;
  onClose: () => void;
}

export default function SuspiciousValuesModal({
  suspiciousReturns,
  onConfirm,
  onReject,
  onOverride,
  isOpen,
  onClose,
}: Props) {
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [showOverrideInputs, setShowOverrideInputs] = useState(false);

  if (!isOpen) return null;

  const handleOverrideChange = (region: string, value: string) => {
    const numValue = parseFloat(value) / 100; // Convert from % to decimal
    if (!isNaN(numValue)) {
      setOverrides((prev) => ({ ...prev, [region]: numValue }));
    }
  };

  const handleConfirmOverrides = () => {
    if (Object.keys(overrides).length > 0) {
      onOverride(overrides);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-yellow-50">
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0">
              <svg
                className="h-6 w-6 text-yellow-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Unusual Expected Returns Detected
              </h3>
              <p className="text-sm text-gray-600">
                Some expected returns are outside the typical range [-5%, +15%]. Please review.
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          <div className="space-y-4">
            {suspiciousReturns.map((item) => (
              <div
                key={item.region}
                className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-semibold text-gray-900">{item.region}</span>
                    <span className="ml-2 text-lg font-bold text-red-600">
                      {(item.return * 100).toFixed(1)}%
                    </span>
                  </div>
                  {item.confidence && (
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        item.confidence === 'high'
                          ? 'bg-green-100 text-green-700'
                          : item.confidence === 'medium'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {item.confidence} confidence
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 mt-1">{item.rationale}</p>
                {item.warningMessage && (
                  <p className="text-sm text-red-600 mt-2 font-medium">{item.warningMessage}</p>
                )}

                {/* Override input */}
                {showOverrideInputs && (
                  <div className="mt-3 flex items-center gap-2">
                    <label className="text-sm text-gray-600">Override value:</label>
                    <input
                      type="number"
                      step="0.5"
                      min="-5"
                      max="15"
                      placeholder={(item.return * 100).toFixed(1)}
                      onChange={(e) => handleOverrideChange(item.region, e.target.value)}
                      className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                    />
                    <span className="text-sm text-gray-500">%</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Info box */}
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>Why does this matter?</strong> Expected returns directly affect your optimal
              portfolio allocation. Unrealistic values can lead to over/under allocation in certain
              regions.
            </p>
          </div>
        </div>

        {/* Footer with actions */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="flex flex-col sm:flex-row gap-3 justify-end">
            <button
              onClick={onReject}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Re-fetch Data
            </button>
            <button
              onClick={() => setShowOverrideInputs(!showOverrideInputs)}
              className="px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
            >
              {showOverrideInputs ? 'Hide Override' : 'Override Values'}
            </button>
            {showOverrideInputs && Object.keys(overrides).length > 0 ? (
              <button
                onClick={handleConfirmOverrides}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Apply Overrides
              </button>
            ) : (
              <button
                onClick={() => {
                  onConfirm();
                  onClose();
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-yellow-600 rounded-lg hover:bg-yellow-700 transition-colors"
              >
                Proceed Anyway
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
