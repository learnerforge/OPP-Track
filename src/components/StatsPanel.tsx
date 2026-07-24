import { useMemo } from 'react';
import type { Opportunity } from '../types/opportunity';
import { todayStr, daysBetween } from '../utils';

interface StatsPanelProps {
  opportunities: Opportunity[];
}

interface StatCard {
  label: string;
  value: number;
  color: string;
  icon: string;
}

export function StatsPanel({ opportunities }: StatsPanelProps) {
  if (opportunities.length === 0) {
    return (
      <div className="text-center py-12 animate-fade-in">
        <div className="text-3xl mb-3">📈</div>
        <p className="text-gray-500 text-sm">
          No data to show yet. Add some opportunities to see your stats.
        </p>
      </div>
    );
  }

  const stats = useMemo(() => {
    const now = todayStr();
    const thisMonth = now.substring(0, 7);

    const monthOpps = opportunities.filter(o => o.date_added.startsWith(thisMonth));

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
      applied: monthOpps.filter(o => o.status === 'Applied' || o.status === 'In Progress' || o.status === 'Completed').length,
      completed: monthOpps.filter(o => o.status === 'Completed').length,
    };

    const byType = {
      hackathon: opportunities.filter(o => o.type === 'Hackathon').length,
      internship: opportunities.filter(o => o.type === 'Internship').length,
      certification: opportunities.filter(o => o.type === 'Certification').length,
    };

    const upcoming = opportunities.filter(
      o => o.status !== 'Completed' && daysBetween(o.deadline, now) >= 0
    ).length;

    const overdue = opportunities.filter(
      o => o.status !== 'Completed' && daysBetween(o.deadline, now) < 0
    ).length;

    return { byStatus, thisMonthStats, byType, upcoming, overdue };
  }, [opportunities]);

  const statusCards: StatCard[] = [
    { label: 'Total Tracked', value: stats.byStatus.total, color: 'bg-gray-100 text-gray-800', icon: '📋' },
    { label: 'Not Started', value: stats.byStatus.notStarted, color: 'bg-slate-100 text-slate-800', icon: '⏳' },
    { label: 'Applied', value: stats.byStatus.applied, color: 'bg-blue-100 text-blue-800', icon: '📤' },
    { label: 'In Progress', value: stats.byStatus.inProgress, color: 'bg-amber-100 text-amber-800', icon: '🔄' },
    { label: 'Completed', value: stats.byStatus.completed, color: 'bg-green-100 text-green-800', icon: '✅' },
    { label: 'Rejected', value: stats.byStatus.rejected, color: 'bg-red-100 text-red-800', icon: '❌' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Statistics</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Overview of your opportunity tracking progress.
        </p>
      </div>

      {/* Status breakdown */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          By Status
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {statusCards.map(card => (
            <div
              key={card.label}
              className={`${card.color} rounded-lg p-4 text-center`}
            >
              <div className="text-2xl mb-1">{card.icon}</div>
              <div className="text-2xl font-bold">{card.value}</div>
              <div className="text-xs font-medium opacity-80">{card.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* This month */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          This Month
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-indigo-700">{stats.thisMonthStats.added}</div>
            <div className="text-xs text-indigo-600 font-medium">Added</div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-700">{stats.thisMonthStats.applied}</div>
            <div className="text-xs text-blue-600 font-medium">Applied</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-700">{stats.thisMonthStats.completed}</div>
            <div className="text-xs text-green-600 font-medium">Completed</div>
          </div>
        </div>
      </div>

      {/* By type */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          By Type
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
            <div className="text-2xl mb-1">🏆</div>
            <div className="text-2xl font-bold text-purple-700">{stats.byType.hackathon}</div>
            <div className="text-xs text-purple-600 font-medium">Hackathons</div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <div className="text-2xl mb-1">💼</div>
            <div className="text-2xl font-bold text-blue-700">{stats.byType.internship}</div>
            <div className="text-xs text-blue-600 font-medium">Internships</div>
          </div>
          <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 text-center">
            <div className="text-2xl mb-1">📜</div>
            <div className="text-2xl font-bold text-teal-700">{stats.byType.certification}</div>
            <div className="text-xs text-teal-600 font-medium">Certifications</div>
          </div>
        </div>
      </div>

      {/* Upcoming + Overdue */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-amber-700">{stats.upcoming}</div>
          <div className="text-xs text-amber-600 font-medium">Upcoming Deadlines</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-red-700">{stats.overdue}</div>
          <div className="text-xs text-red-600 font-medium">Overdue</div>
        </div>
      </div>
    </div>
  );
}
