import type { Opportunity } from '../types/opportunity';
import { OpportunityCard } from './OpportunityCard';
import { daysRemaining, isWithinDays, daysBetween, todayStr } from '../utils';

interface WeeklyReviewModeProps {
  opportunities: Opportunity[];
  onEdit: (opp: Opportunity) => void;
  onDelete: (id: string) => void;
  onChangeStatus: (id: string, status: Opportunity['status']) => void;
}

export function WeeklyReviewMode({
  opportunities,
  onEdit,
  onDelete,
  onChangeStatus,
}: WeeklyReviewModeProps) {
  const closingSoon = opportunities.filter(
    o =>
      o.status !== 'Completed' &&
      daysBetween(o.deadline, todayStr()) >= 0 &&
      isWithinDays(o.deadline, 7)
  );

  const newUnstarted = opportunities.filter(
    o =>
      o.status === 'Not Started' &&
      daysBetween(o.date_added, todayStr()) <= 7 &&
      daysBetween(o.date_added, todayStr()) >= 0
  );

  const merged = new Map<string, Opportunity>();
  for (const opp of closingSoon) merged.set(opp.id, opp);
  for (const opp of newUnstarted) merged.set(opp.id, opp);

  const items = Array.from(merged.values()).sort(
    (a, b) => a.deadline.localeCompare(b.deadline)
  );

  const urgentCount = items.filter(
    o => daysRemaining(o.deadline) <= 2 && daysRemaining(o.deadline) >= 0
  ).length;

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Weekly Review</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Opportunities closing within 7 days or newly added and not yet started.
        </p>
      </div>

      {urgentCount > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2">
          <span className="text-red-500 text-lg">⚠️</span>
          <span className="text-sm text-red-700 font-medium">
            {urgentCount} {urgentCount === 1 ? 'opportunity is' : 'opportunities are'}{' '}
            closing within 2 days!
          </span>
        </div>
      )}

      {items.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-3xl mb-3">✅</div>
          <p className="text-gray-500 text-sm">
            Nothing urgent this week. All caught up!
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map(opp => (
            <OpportunityCard
              key={opp.id}
              opp={opp}
              onEdit={onEdit}
              onDelete={onDelete}
              onChangeStatus={onChangeStatus}
            />
          ))}
        </div>
      )}
    </div>
  );
}
