import { useMemo } from 'react';
import type { Opportunity } from '../types/opportunity';
import { daysBetween, todayStr } from '../utils';

interface HeroProps {
  opportunities: Opportunity[];
}

/* Editorial masthead — a day-aware greeting plus a stat band, the way an
   edition masthead opens a newsletter. */
export function Hero({ opportunities }: HeroProps) {
  const stats = useMemo(() => {
    const now = todayStr();
    const active = opportunities.filter(o => o.status !== 'Completed');
    const closingSoon = active.filter(
      o => daysBetween(o.deadline, now) >= 0 && daysBetween(o.deadline, now) <= 7
    ).length;
    const overdue = active.filter(o => daysBetween(o.deadline, now) < 0).length;
    const applied = opportunities.filter(
      o => o.status === 'Applied' || o.status === 'In Progress'
    ).length;

    const hour = new Date().getHours();
    const greeting =
      hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

    return { total: opportunities.length, closingSoon, overdue, applied, greeting };
  }, [opportunities]);

  return (
    <section className="border-b border-rule bg-paper-raised">
      <div className="mx-auto max-w-5xl px-5 py-8 sm:py-10">
        <p className="kicker mb-3">
          {new Date().toLocaleDateString('en-IN', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
          })}
        </p>

        <h1 className="font-display text-3xl leading-[1.05] font-bold tracking-tight text-ink sm:text-4xl">
          {stats.greeting}.{' '}
          <span className="italic-accent text-ink-soft">
            {stats.total === 0
              ? 'your board is clear.'
              : stats.closingSoon > 0
                ? `${stats.closingSoon} closing this week.`
                : 'nothing closing imminently.'}
          </span>
        </h1>

        <p className="mt-3 max-w-xl text-sm leading-relaxed text-ink-muted">
          Hackathons, internships and certifications — logged once, sorted by
          deadline, colour-coded by how loud the clock is ticking.
        </p>

        {/* Stat band */}
        <dl className="mt-7 grid grid-cols-2 gap-x-6 gap-y-5 border-t border-rule pt-6 sm:grid-cols-4">
          <Stat label="Tracked" value={stats.total} />
          <Stat label="Closing ≤7 days" value={stats.closingSoon} tone={stats.closingSoon > 0 ? 'warning' : undefined} />
          <Stat label="Overdue" value={stats.overdue} tone={stats.overdue > 0 ? 'critical' : undefined} />
          <Stat label="In motion" value={stats.applied} tone="accent" />
        </dl>
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: 'warning' | 'critical' | 'accent';
}) {
  const toneClass =
    tone === 'warning'
      ? 'text-warning'
      : tone === 'critical'
        ? 'text-critical'
        : tone === 'accent'
          ? 'text-accent'
          : 'text-ink';

  return (
    <div>
      <dd className={`font-display text-3xl font-bold tabular-nums ${toneClass}`}>
        {value}
      </dd>
      <dt className="kicker mt-1">{label}</dt>
    </div>
  );
}
