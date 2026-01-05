import { NavLink } from 'react-router-dom';
import { useAppStore } from '../../store';
import { WORKFLOW_STEPS, WorkflowStep } from '../../types';

export default function Sidebar() {
  const { completedSteps } = useAppStore();

  const isComplete = (step: WorkflowStep) => completedSteps.includes(step);

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-[calc(100vh-73px)]">
      <nav className="p-4">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
          Workflow
        </p>
        <ul className="space-y-1">
          {WORKFLOW_STEPS.map((step, index) => (
            <li key={step.id}>
              <NavLink
                to={step.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`
                }
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                    isComplete(step.id)
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {isComplete(step.id) ? '✓' : index + 1}
                </span>
                {step.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
