import { useState } from 'react';

interface Props {
  initialValue: number;
  onSubmit: (value: number) => void;
  loading: boolean;
}

export default function CRRADirectInput({ initialValue, onSubmit, loading }: Props) {
  const [value, setValue] = useState(initialValue);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(value);
  };

  const getProfileLabel = (crra: number): string => {
    if (crra < 2) return 'Very Aggressive';
    if (crra < 3) return 'Aggressive';
    if (crra < 4) return 'Moderate';
    if (crra < 6) return 'Conservative';
    return 'Very Conservative';
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="label">CRRA Value</label>
        <input
          type="range"
          min="1"
          max="10"
          step="0.1"
          value={value}
          onChange={(e) => setValue(parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between mt-2 text-xs text-gray-500">
          <span>1 (Aggressive)</span>
          <span>5</span>
          <span>10 (Conservative)</span>
        </div>
      </div>

      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
        <div>
          <div className="text-3xl font-bold text-primary-600">{value.toFixed(1)}</div>
          <div className="text-sm text-gray-500">{getProfileLabel(value)}</div>
        </div>
        <div className="text-right text-sm text-gray-600">
          <div>Risky allocation: ~{Math.round((1 / value) * 100)}%</div>
          <div>Bond allocation: ~{Math.round((1 - 1 / value) * 100)}%</div>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="btn btn-primary w-full"
      >
        {loading ? 'Processing...' : 'Set Risk Profile'}
      </button>
    </form>
  );
}
