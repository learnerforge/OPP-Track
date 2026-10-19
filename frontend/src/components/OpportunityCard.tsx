import { useState, useEffect, useRef } from 'react';
import type { Opportunity } from '@/types/opportunity';
import { STATUS_OPTIONS } from '@/lib/constants';
import {
  getUrgency,
  getDaysLabel,
  formatDate,
  isExpiredOrCompleted,
} from '@/lib/date';
import { URGENCY_STYLES } from '@/lib/constants';
import { STATUS_META, TYPE_META } from '@/lib/meta';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface OpportunityCardProps {
  opp: Opportunity;
  onEdit: (opp: Opportunity) => void;
  onDelete: (id: string) => void;
  onChangeStatus: (id: string, status: Opportunity['status']) => void;
}

export function OpportunityCard({
  opp,
  onEdit,
  onDelete,
  onChangeStatus,
}: OpportunityCardProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const urgency = getUrgency(opp.deadline, opp.status);
  const styles = URGENCY_STYLES[urgency];
  const expired = isExpiredOrCompleted(opp.deadline, opp.status);
  const daysLabel = getDaysLabel(opp.deadline, opp.status);
  const typeMeta = TYPE_META[opp.type];
  const statusMeta = STATUS_META[opp.status];

  useEffect(() => {
    if (confirmDelete) cancelRef.current?.focus();
  }, [confirmDelete]);

  if (confirmDelete) {
    return (
      <div
        role="alert"
        className="animate-fade-in rounded-lg border border-critical/30 bg-critical-soft p-4"
      >
        <p className="text-sm text-ink-soft">
          Delete <strong className="text-ink">{opp.title}</strong>? This cannot
          be undone.
        </p>
        <div className="mt-3 flex gap-2">
          <Button
            size="sm"
            variant="destructive"
            onClick={() => onDelete(opp.id)}
            aria-label={`Confirm delete ${opp.title}`}
          >
            Delete
          </Button>
          <Button
            ref={cancelRef}
            size="sm"
            variant="outline"
            onClick={() => setConfirmDelete(false)}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <article
      className={cn(
        'group relative overflow-hidden rounded-lg border bg-surface p-4 transition-all hover:shadow-sm sm:p-5',
        styles.border,
        expired && 'opacity-70'
      )}
    >
      <span
        aria-hidden="true"
        className={cn('absolute inset-y-0 left-0 w-1', styles.dot)}
      />

      <div className="flex flex-col gap-3 pl-3 sm:flex-row sm:items-start sm:gap-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-display text-base font-semibold leading-snug tracking-tight text-ink">
              {opp.title}
            </h4>
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
                typeMeta.className
              )}
            >
              <span aria-hidden="true">{typeMeta.glyph}</span>
              {typeMeta.label}
            </span>
          </div>

          {opp.source && (
            <p className="mt-1 font-mono text-xs text-ink-faint">
              via {opp.source}
              {opp.organizer ? ` · ${opp.organizer}` : ''}
            </p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <span
              className={cn(
                'inline-flex items-center rounded-full px-2 py-0.5 font-mono text-[11px] font-medium tracking-wide',
                styles.badge
              )}
              aria-label={`${daysLabel} — urgency: ${urgency}`}
            >
              {daysLabel}
            </span>
            <span className="font-mono text-xs text-ink-muted">
              due {formatDate(opp.deadline)}
            </span>
            {opp.location && (
              <span className="font-mono text-xs text-ink-faint">
                ◎ {opp.location}
              </span>
            )}
            {opp.prize_pool && (
              <span className="font-mono text-xs text-ink-faint">
                {opp.prize_pool}
              </span>
            )}
          </div>

          {opp.eligibility && (
            <p className="mt-2 text-xs leading-relaxed text-ink-soft">
              <span className="kicker mr-1">elig</span>
              {opp.eligibility}
            </p>
          )}

          {opp.tags.length > 0 && (
            <ul className="mt-2.5 flex flex-wrap gap-1.5">
              {opp.tags.map((tag, i) => (
                <li
                  key={i}
                  className="rounded-full border border-rule bg-paper px-2 py-0.5 text-[11px] text-ink-muted"
                >
                  {tag}
                </li>
              ))}
            </ul>
          )}

          {opp.notes && (
            <p className="mt-2 line-clamp-2 text-xs italic text-ink-muted">
              {opp.notes}
            </p>
          )}
        </div>

        <div className="flex shrink-0 flex-row items-center gap-2 sm:flex-col sm:items-end">
          <label className="sr-only" htmlFor={`status-${opp.id}`}>
            Status for {opp.title}
          </label>
          <select
            id={`status-${opp.id}`}
            value={opp.status}
            onChange={e =>
              onChangeStatus(opp.id, e.target.value as Opportunity['status'])
            }
            className={cn(
              'h-8 rounded-full border border-rule bg-transparent px-2.5 text-xs font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
              statusMeta.className
            )}
          >
            {STATUS_OPTIONS.map(s => (
              <option key={s} value={s}>
                {STATUS_META[s].label}
              </option>
            ))}
          </select>

          <div className="flex gap-1.5">
            {opp.link && (
              <a
                href={opp.link}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Open link for ${opp.title}`}
                className="inline-flex h-8 items-center rounded-md border border-rule px-2.5 text-xs font-medium text-ink-soft transition-colors hover:bg-muted"
              >
                Open ↗
              </a>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => onEdit(opp)}
              aria-label={`Edit ${opp.title}`}
              className="h-8 text-xs"
            >
              Edit
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setConfirmDelete(true)}
              aria-label={`Delete ${opp.title}`}
              className="h-8 border-critical/30 text-critical hover:bg-critical-soft"
            >
              Delete
            </Button>
          </div>
        </div>
      </div>
    </article>
  );
}
