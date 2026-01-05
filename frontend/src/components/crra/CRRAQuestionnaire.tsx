import { useState } from 'react';

interface Props {
  onSubmit: (responses: {
    lossThreshold: number;
    riskPercentage: number;
    stockAllocation: number;
    safeChoice: number;
  }) => void;
  loading: boolean;
}

interface Question {
  id: keyof Props extends 'onSubmit' ? never : string;
  title: string;
  description: string;
  min: number;
  max: number;
  minLabel: string;
  maxLabel: string;
  unit: string;
}

const questions: Question[] = [
  {
    id: 'lossThreshold',
    title: 'Loss Tolerance',
    description:
      'Imagine you have €100,000 in savings. What is the maximum percentage loss you could tolerate in one year before switching to a more conservative investment?',
    min: 0,
    max: 100,
    minLabel: '0% (No loss)',
    maxLabel: '100% (Any loss)',
    unit: '%',
  },
  {
    id: 'riskPercentage',
    title: 'Risk Assessment',
    description:
      "You're offered a one-time investment: 50% chance to increase your wealth by 50%, 50% chance to lose X%. What is the maximum loss you would accept?",
    min: 0,
    max: 100,
    minLabel: '0% (No risk)',
    maxLabel: '100% (Equal risk)',
    unit: '%',
  },
  {
    id: 'stockAllocation',
    title: 'Portfolio Preference',
    description:
      'In a long-term investment portfolio, what percentage would you ideally allocate to risky assets (stocks, commodities) vs safe assets (bonds, cash)?',
    min: 0,
    max: 100,
    minLabel: '0% Risky',
    maxLabel: '100% Risky',
    unit: '% risky',
  },
  {
    id: 'safeChoice',
    title: 'Income Security',
    description:
      "If offered two jobs: A) Fixed salary at your current level, or B) Variable salary averaging 30% higher but with significant variations. What probability of job security in option B would you require to choose it?",
    min: 0,
    max: 100,
    minLabel: '0% (Take any risk)',
    maxLabel: '100% (Need certainty)',
    unit: '%',
  },
];

export default function CRRAQuestionnaire({ onSubmit, loading }: Props) {
  const [responses, setResponses] = useState({
    lossThreshold: 25,
    riskPercentage: 25,
    stockAllocation: 50,
    safeChoice: 70,
  });

  const handleChange = (id: string, value: number) => {
    setResponses((prev) => ({ ...prev, [id]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(responses);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {questions.map((q, index) => (
        <div key={q.id} className="space-y-3">
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-8 h-8 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-sm font-medium">
              {index + 1}
            </span>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900">{q.title}</h4>
              <p className="text-sm text-gray-500 mt-1">{q.description}</p>
            </div>
          </div>

          <div className="ml-11">
            <input
              type="range"
              min={q.min}
              max={q.max}
              value={responses[q.id as keyof typeof responses]}
              onChange={(e) => handleChange(q.id, parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between mt-1 text-xs text-gray-500">
              <span>{q.minLabel}</span>
              <span className="font-medium text-primary-600">
                {responses[q.id as keyof typeof responses]}
                {q.unit}
              </span>
              <span>{q.maxLabel}</span>
            </div>
          </div>
        </div>
      ))}

      <button
        type="submit"
        disabled={loading}
        className="btn btn-primary w-full"
      >
        {loading ? 'Calculating...' : 'Calculate My Risk Profile'}
      </button>
    </form>
  );
}
