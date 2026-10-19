import type { Opportunity } from '@/types/opportunity';
import { TYPE_OPTIONS } from '@/lib/constants';
import { daysBetween, todayStr } from '@/lib/date';

interface StatsPanelProps {
  opportunities: Opportunity[];
}

interface Stat {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}

export function StatsPanel({ opportunities }: StatsPanelProps) {
  const today = todayStr();
  const total = opportunities.length;

  const dueThisWeek = opportunities.filter(o => {
    const d = daysBetween(o.deadline, today);
    return d >= 0 && d <= 7;
  }).length;

  const dueToday = opportunities.filter(
    o => daysBetween(o.deadline, today) === 0
  ).length;

  const completed = opportunities.filter(o => o.status === 'Completed').length;
  const applied = opportunities.filter(o => o.status === 'Applied').length;
  const inProgress = opportunities.filter(
    o => o.status === 'In Progress'
  ).length;

  const expired = opportunities.filter(
    o => daysBetween(o.deadline, today) < 0
  ).length;

  const completionRate =
    total > 0 ? Math.round((completed / total) * 100) : 0;

  const byType = TYPE_OPTIONS.map(t => ({
    type: t,
    count: opportunities.filter(o => o.type === t).length,
  }));

  const maxTypeCount = Math.max(1, ...byType.map(b => b.count));

  const stats: Stat[] = [
    { label: 'tracked', value: total, sub: 'total entries' },
    { label: 'due this week', value: dueThisWeek, sub: 'next 7 days', accent: dueThisWeek > 0 },
    { label: 'due today', value: dueToday, sub: 'deadline hits', accent: dueToday > 0 },
    { label: 'applied', value: applied, sub: 'out for review' },
    { label: 'in progress', value: inProgress, sub: 'being worked' },
    { label: 'done', value: completed, sub: `${completionRate}% completion` },
    { label: 'expired', value: expired, sub: 'past deadline' },
  ];

  return (
    <section aria-label="Statistics" className="space-y-6">
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-rule bg-rule sm:grid-cols-4 lg:grid-cols-7">
        {stats.map(s => (
          <div key={s.label} className="bg-surface p-4">
            <p className="kicker">{s.label}</p>
            <p
              className={`mt-1 font-display text-3xl font-bold tracking-tight ${
                s.accent ? 'text-critical' : 'text-ink'
              }`}
            >
              {s.value}
            </p>
            {s.sub && (
              <p className="mt-0.5 font-mono text-[11px] text-ink-faint">
                {s.sub}
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-rule bg-surface p-5">
        <p className="kicker mb-4">by category</p>
        <ul className="space-y-3">
          {byType.map(b => (
            <li key={b.type} className="flex items-center gap-3">
              <span className="w-24 shrink-0 font-mono text-xs uppercase tracking-wide text-ink-muted">
                {b.type}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-ink transition-all"
                  style={{ width: `${(b.count / maxTypeCount) * 100}%` }}
                  aria-hidden="true"
                />
              </div>
              <span className="w-6 shrink-0 text-right font-mono text-xs text-ink-soft">
                {b.count}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
