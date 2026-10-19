import type { Opportunity } from '../types/opportunity';
import { OpportunityCard } from './OpportunityCard';
import { Alert, AlertTitle, AlertDescription } from './ui/alert';
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
    <section className="animate-fade-in space-y-5">
      <header>
        <p className="kicker mb-2">the week ahead</p>
        <h2 className="font-display text-2xl font-bold tracking-tight text-ink">
          Weekly review
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          Opportunities closing within 7 days or newly added and not yet started.
        </p>
      </header>

      {urgentCount > 0 && (
        <Alert variant="destructive" className="border-critical/30 bg-critical-soft">
          <svg
            className="h-4 w-4 text-critical"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"
            />
          </svg>
          <AlertTitle className="text-critical">
            {urgentCount}{' '}
            {urgentCount === 1 ? 'opportunity is' : 'opportunities are'} closing
            within 2 days!
          </AlertTitle>
          <AlertDescription className="text-critical/90">
            Treat these as the top of your list this week.
          </AlertDescription>
        </Alert>
      )}

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-rule py-12 text-center">
          <p className="kicker mb-2">all clear</p>
          <p className="text-sm text-ink-muted">
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
    </section>
  );
}
