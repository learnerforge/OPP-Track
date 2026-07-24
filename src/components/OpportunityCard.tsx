import { useState, useEffect, useRef } from 'react';
import type { Opportunity } from '../types/opportunity';
import { STATUS_OPTIONS } from '../constants';
import {
  getUrgency,
  getDaysLabel,
  formatDate,
  isExpiredOrCompleted,
  URGENCY_STYLES,
  TYPE_COLORS,
} from '../utils';

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

  useEffect(() => {
    if (confirmDelete) {
      cancelRef.current?.focus();
    }
  }, [confirmDelete]);

  if (confirmDelete) {
    return (
      <div
        role="alert"
        className="bg-red-50 border border-red-200 rounded-lg p-4 animate-fade-in"
      >
        <p className="text-sm text-red-700 mb-3">
          Delete <strong>{opp.title}</strong>? This cannot be undone.
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => onDelete(opp.id)}
            className="bg-red-600 hover:bg-red-700 text-white text-xs font-medium px-3 py-2 rounded-md transition-colors min-h-[36px]"
            aria-label={`Confirm delete ${opp.title}`}
          >
            Delete
          </button>
          <button
            ref={cancelRef}
            onClick={() => setConfirmDelete(false)}
            className="bg-white hover:bg-gray-100 text-gray-600 text-xs font-medium px-3 py-2 rounded-md border border-gray-200 transition-colors min-h-[36px]"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`${styles.bg} border ${styles.border} rounded-lg p-4 transition-all hover:shadow-sm ${
        expired ? 'opacity-75' : ''
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2">
            <div
              className={`w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0 ${styles.dot}`}
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="font-semibold text-gray-900 text-sm truncate">
                  {opp.title}
                </h4>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    TYPE_COLORS[opp.type] || 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {opp.type}
                </span>
              </div>

              {opp.source && (
                <p className="text-xs text-gray-500 mt-0.5">via {opp.source}</p>
              )}

              <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${styles.badge}`}
                  aria-label={`${daysLabel} — urgency: ${urgency}`}
                >
                  {daysLabel}
                </span>
                <span className="text-xs text-gray-500">
                  Due {formatDate(opp.deadline)}
                </span>
              </div>

              {opp.eligibility && (
                <p className="text-xs text-gray-600 mt-1.5">
                  <span className="font-medium">Eligibility:</span>{' '}
                  {opp.eligibility}
                </p>
              )}

              {opp.tags.length > 0 && (
                <div className="flex gap-1.5 mt-2 flex-wrap">
                  {opp.tags.map((tag, i) => (
                    <span
                      key={i}
                      className="text-xs bg-white/80 border border-gray-200 text-gray-600 px-2 py-0.5 rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {opp.notes && (
                <p className="text-xs text-gray-500 mt-1.5 line-clamp-2 italic">
                  {opp.notes}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-row sm:flex-col gap-2 flex-shrink-0 items-center">
          <select
            value={opp.status}
            onChange={e =>
              onChangeStatus(opp.id, e.target.value as Opportunity['status'])
            }
            aria-label={`Status for ${opp.title}`}
            className="text-xs border border-gray-200 rounded-md px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-indigo-500 min-h-[36px]"
          >
            {STATUS_OPTIONS.map(s => (
              <option key={s} value={s}>
                {s}
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
                className="text-xs bg-white border border-gray-200 text-indigo-600 px-2.5 py-2 rounded-md hover:bg-indigo-50 transition-colors min-h-[36px] flex items-center"
              >
                Link ↗
              </a>
            )}
            <button
              onClick={() => onEdit(opp)}
              aria-label={`Edit ${opp.title}`}
              className="text-xs bg-white border border-gray-200 text-gray-600 px-2.5 py-2 rounded-md hover:bg-gray-50 transition-colors min-h-[36px]"
            >
              Edit
            </button>
            <button
              onClick={() => setConfirmDelete(true)}
              aria-label={`Delete ${opp.title}`}
              className="text-xs bg-white border border-gray-200 text-red-500 px-2.5 py-2 rounded-md hover:bg-red-50 transition-colors min-h-[36px]"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
