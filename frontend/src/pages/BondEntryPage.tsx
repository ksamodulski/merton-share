import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store';

export default function BondEntryPage() {
  const navigate = useNavigate();
  const { bondPosition, setBondPosition, markStepComplete } = useAppStore();

  const [formData, setFormData] = useState({
    amountPln: bondPosition?.amountPln ?? 100000,
    yieldRate: bondPosition?.yieldRate ?? 0.06,
    lockDate: bondPosition?.lockDate ?? '2030-01-01',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setBondPosition({
      amountPln: formData.amountPln,
      yieldRate: formData.yieldRate,
      lockDate: formData.lockDate,
    });
    markStepComplete('bonds');
    navigate('/portfolio');
  };

  const handleSkip = () => {
    setBondPosition(null);
    markStepComplete('bonds');
    navigate('/portfolio');
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Bond Position</h2>
        <p className="mt-1 text-gray-500">
          Enter your Polish inflation-linked bond details (optional).
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-6">
        <div>
          <label className="label">Amount (PLN)</label>
          <input
            type="number"
            value={formData.amountPln}
            onChange={(e) =>
              setFormData({ ...formData, amountPln: parseFloat(e.target.value) || 0 })
            }
            className="input"
            min="0"
            step="1000"
          />
          <p className="mt-1 text-sm text-gray-500">
            Your bond position in Polish Zloty
          </p>
        </div>

        <div>
          <label className="label">Annual Yield (%)</label>
          <input
            type="number"
            value={(formData.yieldRate * 100).toFixed(1)}
            onChange={(e) =>
              setFormData({
                ...formData,
                yieldRate: (parseFloat(e.target.value) || 0) / 100,
              })
            }
            className="input"
            min="0"
            max="20"
            step="0.1"
          />
          <p className="mt-1 text-sm text-gray-500">
            Expected annual yield (e.g., 6% for COI bonds)
          </p>
        </div>

        <div>
          <label className="label">Lock-until Date</label>
          <input
            type="date"
            value={formData.lockDate}
            onChange={(e) =>
              setFormData({ ...formData, lockDate: e.target.value })
            }
            className="input"
          />
          <p className="mt-1 text-sm text-gray-500">
            When the bonds mature or become liquid
          </p>
        </div>

        <div className="flex gap-3 pt-4">
          <button type="submit" className="btn btn-primary flex-1">
            Save & Continue
          </button>
          <button
            type="button"
            onClick={handleSkip}
            className="btn btn-secondary"
          >
            Skip
          </button>
        </div>
      </form>
    </div>
  );
}
