import { useState } from 'react';
import type { Opportunity } from '../types/opportunity';
import { OpportunityCard } from './OpportunityCard';
import { cn } from '../lib/utils';

interface ArchiveSectionProps {
  archived: Opportunity[];
  onEdit: (opp: Opportunity) => void;
  onDelete: (id: string) => void;
  onChangeStatus: (id: string, status: Opportunity['status']) => void;
}

export function ArchiveSection({
  archived,
  onEdit,
  onDelete,
  onChangeStatus,
}: ArchiveSectionProps) {
  const [open, setOpen] = useState(false);

  return (
    <section aria-label="Archived opportunities">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="group flex min-h-[36px] items-center gap-2 px-1 text-sm font-semibold uppercase tracking-wide text-ink-faint transition-colors hover:text-ink-muted"
      >
        <svg
          className={cn(
            'h-3.5 w-3.5 transition-transform',
            open && 'rotate-90'
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path d="m9 18 6-6-6-6" />
        </svg>
        <span className="kicker text-inherit">
          archive ({archived.length})
        </span>
      </button>
      {open && (
        <div className="space-y-2 animate-fade-in pt-2" role="list">
          {archived.map(opp => (
            <div role="listitem" key={opp.id}>
              <OpportunityCard
                opp={opp}
                onEdit={onEdit}
                onDelete={onDelete}
                onChangeStatus={onChangeStatus}
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
