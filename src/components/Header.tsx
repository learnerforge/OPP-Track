import type { ViewMode } from '../types/opportunity';

interface HeaderProps {
  viewMode: ViewMode;
  onViewChange: (mode: ViewMode) => void;
  onAdd: () => void;
  showForm: boolean;
  remindersEnabled?: boolean;
  remindersSupported?: boolean;
  onToggleReminders?: () => void;
}

const NAV_ITEMS: { mode: ViewMode; label: string; icon: string }[] = [
  { mode: 'dashboard', label: 'Dashboard', icon: '📊' },
  { mode: 'weekly-review', label: 'Weekly Review', icon: '📋' },
  { mode: 'stats', label: 'Stats', icon: '📈' },
];

export function Header({
  viewMode,
  onViewChange,
  onAdd,
  showForm,
  remindersEnabled = false,
  remindersSupported = false,
  onToggleReminders,
}: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
      <div className="max-w-4xl mx-auto px-4">
        <div className="flex items-center justify-between py-3">
          <div className="flex items-center gap-2.5">
            <span className="text-xl" aria-hidden="true">🎯</span>
            <h1 className="text-lg font-bold text-gray-900">OppTrack</h1>
          </div>
          <div className="flex items-center gap-2">
            {remindersSupported && onToggleReminders && (
              <button
                onClick={onToggleReminders}
                aria-label={
                  remindersEnabled
                    ? 'Disable reminders'
                    : 'Enable browser reminders for deadlines within 2 days'
                }
                aria-pressed={remindersEnabled}
                title={
                  remindersEnabled
                    ? 'Reminders on'
                    : 'Enable reminders for deadlines within 2 days'
                }
                className={`relative flex items-center justify-center w-[44px] h-[44px] rounded-lg border transition-colors ${
                  remindersEnabled
                    ? 'bg-amber-50 border-amber-300'
                    : 'bg-white border-gray-200 hover:bg-gray-50'
                }`}
              >
                <span className="text-base" aria-hidden="true">
                  {remindersEnabled ? '🔔' : '🔕'}
                </span>
                {remindersEnabled && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-amber-500 rounded-full" aria-hidden="true" />
                )}
              </button>
            )}
            <button
              onClick={onAdd}
              aria-label={showForm ? 'Close form' : 'Add new opportunity'}
              className="bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-medium px-4 py-2.5 rounded-lg text-sm transition-colors min-h-[44px]"
            >
              {showForm ? 'Close' : '+ Add'}
            </button>
          </div>
        </div>

        <nav aria-label="Main navigation">
          <div className="flex gap-1 -mb-px overflow-x-auto">
            {NAV_ITEMS.map(item => (
              <button
                key={item.mode}
                onClick={() => onViewChange(item.mode)}
                aria-current={viewMode === item.mode ? 'page' : undefined}
                className={`flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap min-h-[44px] ${
                  viewMode === item.mode
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        </nav>
      </div>
    </header>
  );
}
