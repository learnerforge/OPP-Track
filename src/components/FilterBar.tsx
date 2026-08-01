import type { Filters, OpportunityType, OpportunityStatus, SortKey } from '../types/opportunity';
import { TYPE_OPTIONS, STATUS_OPTIONS } from '../constants';

interface FilterBarProps {
  filters: Filters;
  onFilterChange: (filters: Filters) => void;
  sources: string[];
  allTags: string[];
  activeCount: number;
  totalCount: number;
}

const SORT_LABELS: Record<SortKey, string> = {
  deadline: 'Deadline',
  date_added: 'Date Added',
  title: 'Title',
};

const DUE_WITHIN_OPTIONS = [
  { value: 0, label: 'Any time' },
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
];

export function FilterBar({
  filters,
  onFilterChange,
  sources,
  allTags,
  activeCount,
  totalCount,
}: FilterBarProps) {
  function update<K extends keyof Filters>(key: K, value: Filters[K]) {
    onFilterChange({ ...filters, [key]: value });
  }

  const hasActiveFilters =
    filters.search ||
    filters.type !== 'All' ||
    filters.status !== 'All' ||
    filters.source !== 'All' ||
    filters.tag !== 'All' ||
    filters.dueWithin > 0 ||
    filters.sortKey !== 'deadline' ||
    filters.sortDir !== 'asc';

  function clearFilters() {
    onFilterChange({
      search: '',
      type: 'All',
      status: 'All',
      source: 'All',
      tag: 'All',
      sortKey: 'deadline',
      sortDir: 'asc',
      dueWithin: 0,
    });
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 space-y-3">
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
        <div className="relative flex-1 min-w-0 w-full sm:w-auto">
          <input
            type="text"
            value={filters.search}
            onChange={e => update('search', e.target.value)}
            placeholder="Search title..."
            aria-label="Search opportunities by title"
            className="pl-8 pr-3 py-2 border border-gray-200 rounded-md text-sm w-full focus:outline-none focus:ring-1 focus:ring-indigo-500 min-h-[40px]"
          />
          <svg
            className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
        </div>

        <select
          value={filters.type}
          onChange={e => update('type', e.target.value as OpportunityType | 'All')}
          aria-label="Filter by type"
          className="border border-gray-200 rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 min-h-[40px]"
        >
          <option value="All">All Types</option>
          {TYPE_OPTIONS.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <select
          value={filters.status}
          onChange={e => update('status', e.target.value as OpportunityStatus | 'All')}
          aria-label="Filter by status"
          className="border border-gray-200 rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 min-h-[40px]"
        >
          <option value="All">All Statuses</option>
          {STATUS_OPTIONS.map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {sources.length > 0 && (
          <select
            value={filters.source}
            onChange={e => update('source', e.target.value)}
            aria-label="Filter by source"
            className="border border-gray-200 rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 min-h-[40px]"
          >
            <option value="All">All Sources</option>
            {sources.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        )}

        {allTags.length > 0 && (
          <select
            value={filters.tag}
            onChange={e => update('tag', e.target.value)}
            aria-label="Filter by tag"
            className="border border-gray-200 rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 min-h-[40px]"
          >
            <option value="All">All Tags</option>
            {allTags.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        )}
      </div>

      <div className="flex flex-col sm:flex-row gap-3 sm:items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-400">Due within:</span>
          {DUE_WITHIN_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => update('dueWithin', opt.value)}
              aria-pressed={filters.dueWithin === opt.value}
              className={`text-xs font-medium px-2.5 py-1.5 rounded-full border transition-colors min-h-[32px] ${
                filters.dueWithin === opt.value
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">Sort by:</span>
          <select
            value={filters.sortKey}
            onChange={e => update('sortKey', e.target.value as SortKey)}
            aria-label="Sort opportunities"
            className="border border-gray-200 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 min-h-[32px]"
          >
            {(Object.keys(SORT_LABELS) as SortKey[]).map(key => (
              <option key={key} value={key}>{SORT_LABELS[key]}</option>
            ))}
          </select>
          <button
            onClick={() => update('sortDir', filters.sortDir === 'asc' ? 'desc' : 'asc')}
            aria-label={
              filters.sortDir === 'asc' ? 'Sort ascending, switch to descending' : 'Sort descending, switch to ascending'
            }
            className="text-xs bg-white border border-gray-200 text-gray-600 px-2.5 py-1.5 rounded-md hover:bg-gray-50 transition-colors font-medium min-h-[32px]"
          >
            {filters.sortDir === 'asc' ? '↑ Asc' : '↓ Desc'}
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400" aria-live="polite">
          {activeCount} of {totalCount} shown
        </span>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium min-h-[36px] px-2"
          >
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
}
