import { useState } from 'react';
import type { Opportunity } from '../types/opportunity';
import { OpportunityCard } from './OpportunityCard';

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
    <div>
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center gap-2 text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2 px-1 hover:text-gray-600 transition-colors min-h-[36px]"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path d="m9 18 6-6-6-6" />
        </svg>
        Archive ({archived.length})
      </button>
      {open && (
        <div className="space-y-2 animate-fade-in" role="list">
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
    </div>
  );
}
