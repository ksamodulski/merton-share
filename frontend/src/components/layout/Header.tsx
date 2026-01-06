import { useAppStore } from '../../store';

export default function Header() {
  const { resetAll, crra, portfolio } = useAppStore();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">M</span>
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Merton Portfolio</h1>
            <p className="text-sm text-gray-500">Optimal Asset Allocation</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {crra && (
            <span className="text-sm text-gray-600">
              CRRA: <span className="font-medium">{crra.toFixed(1)}</span>
            </span>
          )}
          {portfolio && (
            <span className="text-sm text-gray-600">
              Portfolio: <span className="font-medium">€{portfolio.totalValueEur.toLocaleString()}</span>
            </span>
          )}
          <button
            onClick={resetAll}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Reset
          </button>
        </div>
      </div>
    </header>
  );
}
