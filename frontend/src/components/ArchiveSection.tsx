import { useState } from 'react';
import type { Opportunity } from '@/types/opportunity';
import { formatDate } from '@/lib/date';
import { STATUS_META, TYPE_META } from '@/lib/meta';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ArchiveSectionProps {
  opportunities: Opportunity[];
  onRestore: (opp: Opportunity) => void;
  onDelete: (id: string) => void;
}

export function ArchiveSection({
  opportunities,
  onRestore,
  onDelete,
}: ArchiveSectionProps) {
  const [open, setOpen] = useState(false);

  if (opportunities.length === 0) return null;

  return (
    <section aria-label="Archive" className="rounded-xl border border-rule bg-surface">
      <button
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        aria-controls="archive-list"
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left transition-colors hover:bg-muted/50 focus-ring rounded-xl"
      >
        <div className="flex items-baseline gap-3">
          <span className="font-display text-base font-semibold tracking-tight text-ink">
            Archive
          </span>
          <span className="font-mono text-xs text-ink-faint">
            {opportunities.length} closed · completed or expired
          </span>
        </div>
        <span
          className={cn(
            'font-mono text-xs text-ink-muted transition-transform',
            open && 'rotate-180'
          )}
          aria-hidden="true"
        >
          ▾
        </span>
      </button>

      {open && (
        <ul
          id="archive-list"
          className="divide-y divide-rule border-t border-rule"
        >
          {opportunities.map(opp => {
            const typeMeta = TYPE_META[opp.type];
            const statusMeta = STATUS_META[opp.status];
            return (
              <li
                key={opp.id}
                className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="truncate font-display text-sm font-semibold text-ink">
                      {opp.title}
                    </h4>
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px]',
                        typeMeta.className
                      )}
                    >
                      {typeMeta.glyph} {typeMeta.label}
                    </span>
                    <span
                      className={cn(
                        'inline-flex rounded-full px-2 py-0.5 font-mono text-[11px]',
                        statusMeta.className
                      )}
                    >
                      {statusMeta.label}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[11px] text-ink-faint">
                    due {formatDate(opp.deadline)}
                  </p>
                </div>

                <div className="flex shrink-0 gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onRestore(opp)}
                    aria-label={`Restore ${opp.title} to active`}
                    className="h-8 text-xs"
                  >
                    Restore
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onDelete(opp.id)}
                    aria-label={`Delete ${opp.title} permanently`}
                    className="h-8 border-critical/30 text-critical hover:bg-critical-soft"
                  >
                    Delete
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
