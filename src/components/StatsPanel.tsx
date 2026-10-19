import { useMemo } from 'react';
import type { Opportunity } from '../types/opportunity';
import { todayStr, daysBetween } from '../utils';

interface StatsPanelProps {
  opportunities: Opportunity[];
}

interface StatCard {
  label: string;
  value: number;
  tone: string;
  num: string;
}

export function StatsPanel({ opportunities }: StatsPanelProps) {
  const stats = useMemo(() => {
    if (opportunities.length === 0) return null;

    const now = todayStr();
    const thisMonth = now.substring(0, 7);

    const monthOpps = opportunities.filter(o =>
      o.date_added.startsWith(thisMonth)
    );

    const byStatus = {
      total: opportunities.length,
      notStarted: opportunities.filter(o => o.status === 'Not Started').length,
      applied: opportunities.filter(o => o.status === 'Applied').length,
      inProgress: opportunities.filter(o => o.status === 'In Progress').length,
      rejected: opportunities.filter(o => o.status === 'Rejected').length,
      completed: opportunities.filter(o => o.status === 'Completed').length,
    };

    const thisMonthStats = {
      added: monthOpps.length,
      applied: monthOpps.filter(
        o =>
          o.status === 'Applied' ||
          o.status === 'In Progress' ||
          o.status === 'Completed'
      ).length,
      completed: monthOpps.filter(o => o.status === 'Completed').length,
    };

    const byType = {
      hackathon: opportunities.filter(o => o.type === 'Hackathon').length,
      internship: opportunities.filter(o => o.type === 'Internship').length,
      certification: opportunities.filter(o => o.type === 'Certification').length,
      competition: opportunities.filter(o => o.type === 'Competition').length,
    };

    const upcoming = opportunities.filter(
      o => o.status !== 'Completed' && daysBetween(o.deadline, now) >= 0
    ).length;

    const overdue = opportunities.filter(
      o => o.status !== 'Completed' && daysBetween(o.deadline, now) < 0
    ).length;

    return { byStatus, thisMonthStats, byType, upcoming, overdue };
  }, [opportunities]);

  if (!stats) {
    return (
      <div className="animate-fade-in rounded-lg border border-dashed border-rule py-16 text-center">
        <p className="kicker mb-2">no data</p>
        <p className="text-sm text-ink-muted">
          No data to show yet. Add some opportunities to see your stats.
        </p>
      </div>
    );
  }

  const statusCards: StatCard[] = [
    { label: 'Total tracked', value: stats.byStatus.total, tone: 'text-ink', num: '01' },
    { label: 'Not started', value: stats.byStatus.notStarted, tone: 'text-ink-muted', num: '02' },
    { label: 'Applied', value: stats.byStatus.applied, tone: 'text-accent', num: '03' },
    { label: 'In progress', value: stats.byStatus.inProgress, tone: 'text-warning', num: '04' },
    { label: 'Completed', value: stats.byStatus.completed, tone: 'text-safe', num: '05' },
    { label: 'Rejected', value: stats.byStatus.rejected, tone: 'text-critical', num: '06' },
  ];

  return (
    <section className="animate-fade-in space-y-8">
      <header>
        <p className="kicker mb-2">the numbers</p>
        <h2 className="font-display text-2xl font-bold tracking-tight text-ink">
          Statistics
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          Overview of your opportunity tracking progress.
        </p>
      </header>

      {/* By status — editorial stat band */}
      <section aria-labelledby="stats-status">
        <h3
          id="stats-status"
          className="kicker mb-3 border-b border-rule pb-2"
        >
          by status
        </h3>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-6 sm:grid-cols-3">
          {statusCards.map(card => (
            <div key={card.label}>
              <span className="section-num" aria-hidden="true">
                {card.num}
              </span>
              <dd
                className={`font-display text-4xl font-bold tabular-nums ${card.tone}`}
              >
                {card.value}
              </dd>
              <dt className="kicker mt-1">{card.label}</dt>
            </div>
          ))}
        </dl>
      </section>

      {/* This month */}
      <section aria-labelledby="stats-month">
        <h3
          id="stats-month"
          className="kicker mb-3 border-b border-rule pb-2"
        >
          this month
        </h3>
        <dl className="grid grid-cols-3 gap-4">
          <MiniStat label="Added" value={stats.thisMonthStats.added} tone="text-ink" />
          <MiniStat label="Applied" value={stats.thisMonthStats.applied} tone="text-accent" />
          <MiniStat label="Completed" value={stats.thisMonthStats.completed} tone="text-safe" />
        </dl>
      </section>

      {/* By type */}
      <section aria-labelledby="stats-type">
        <h3 id="stats-type" className="kicker mb-3 border-b border-rule pb-2">
          by type
        </h3>
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <TypeStat glyph="◆" label="Hackathons" value={stats.byType.hackathon} tone="text-accent" />
          <TypeStat glyph="▲" label="Internships" value={stats.byType.internship} tone="text-safe" />
          <TypeStat glyph="●" label="Certifications" value={stats.byType.certification} tone="text-warning" />
          <TypeStat glyph="■" label="Competitions" value={stats.byType.competition} tone="text-critical" />
        </dl>
      </section>

      {/* Upcoming + Overdue */}
      <dl className="grid grid-cols-2 gap-4">
        <MiniStat
          label="Upcoming deadlines"
          value={stats.upcoming}
          tone="text-warning"
        />
        <MiniStat label="Overdue" value={stats.overdue} tone="text-critical" />
      </dl>
    </section>
  );
}

function MiniStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: string;
}) {
  return (
    <div className="rounded-lg border border-rule bg-surface p-4">
      <dd className={`font-display text-3xl font-bold tabular-nums ${tone}`}>
        {value}
      </dd>
      <dt className="kicker mt-1">{label}</dt>
    </div>
  );
}

function TypeStat({
  glyph,
  label,
  value,
  tone,
}: {
  glyph: string;
  label: string;
  value: number;
  tone: string;
}) {
  return (
    <div className="rounded-lg border border-rule bg-surface p-4">
      <span className={`${tone} text-sm`} aria-hidden="true">
        {glyph}
      </span>
      <dd className={`font-display text-3xl font-bold tabular-nums ${tone}`}>
        {value}
      </dd>
      <dt className="kicker mt-1">{label}</dt>
    </div>
  );
}
