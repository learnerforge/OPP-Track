import type { ViewMode } from '../types/opportunity';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

interface HeaderProps {
  viewMode: ViewMode;
  onViewChange: (mode: ViewMode) => void;
  onAdd: () => void;
  showForm: boolean;
  remindersEnabled?: boolean;
  remindersSupported?: boolean;
  onToggleReminders?: () => void;
}

const NAV_ITEMS: { mode: ViewMode; label: string; num: string }[] = [
  { mode: 'dashboard', label: 'Dashboard', num: '01' },
  { mode: 'weekly-review', label: 'Weekly Review', num: '02' },
  { mode: 'stats', label: 'Stats', num: '03' },
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
    <header className="sticky top-0 z-40 border-b border-rule bg-paper/85 backdrop-blur-md">
      <div className="mx-auto max-w-5xl px-5">
        <div className="flex items-center justify-between gap-4 py-3.5">
          {/* Wordmark */}
          <a href="#top" className="group flex items-baseline gap-2">
            <span
              className="font-display text-xl font-bold tracking-tight text-ink"
              aria-hidden="true"
            >
              OppTrack
            </span>
            <span className="kicker hidden sm:inline text-ink-faint">
              / opportunities, sorted
            </span>
          </a>

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
                className={cn(
                  'relative flex h-9 items-center gap-2 rounded-full border px-3 text-xs font-medium transition-colors',
                  remindersEnabled
                    ? 'border-warning/40 bg-warning/10 text-warning'
                    : 'border-rule bg-transparent text-ink-muted hover:bg-muted'
                )}
              >
                <span aria-hidden="true" className="text-sm leading-none">
                  {remindersEnabled ? '🔔' : '🔕'}
                </span>
                <span className="hidden sm:inline">
                  {remindersEnabled ? 'On' : 'Remind'}
                </span>
                {remindersEnabled && (
                  <span
                    className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-warning"
                    aria-hidden="true"
                  />
                )}
              </button>
            )}

            <Button
              onClick={onAdd}
              aria-label={showForm ? 'Close form' : 'Add new opportunity'}
              size="sm"
              className="rounded-full"
            >
              {showForm ? 'Close' : '＋ Add'}
            </Button>
          </div>
        </div>

        {/* Nav */}
        <nav aria-label="Main navigation">
          <ul className="-mb-px flex gap-5 overflow-x-auto">
            {NAV_ITEMS.map(item => {
              const active = viewMode === item.mode;
              return (
                <li key={item.mode} className="shrink-0">
                  <button
                    onClick={() => onViewChange(item.mode)}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'group relative flex min-h-[40px] items-center gap-2 border-b-2 pb-2.5 pt-1 text-sm transition-colors',
                      active
                        ? 'border-ink text-ink'
                        : 'border-transparent text-ink-muted hover:text-ink'
                    )}
                  >
                    <span className="section-num" aria-hidden="true">
                      {item.num}
                    </span>
                    <span className="font-medium">{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </header>
  );
}
