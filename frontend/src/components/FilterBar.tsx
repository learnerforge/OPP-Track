import type {
  Filters,
  OpportunityType,
  OpportunityStatus,
  SortKey,
} from '@/types/opportunity';
import { TYPE_OPTIONS, STATUS_OPTIONS } from '@/lib/constants';
import { TYPE_META, STATUS_META } from '@/lib/meta';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

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
  date_added: 'Date added',
  title: 'Title',
};

const DUE_WITHIN_OPTIONS = [
  { value: 0, label: 'Any time' },
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
];

// Radix Select can't take an empty string as a value, so "All" uses a sentinel.
const ALL = '__all__';

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
    <section
      aria-label="Filter and sort opportunities"
      className="rounded-xl border border-rule bg-surface p-4"
    >
      <div className="flex flex-col gap-3">
        <div className="relative">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <Input
            type="text"
            value={filters.search}
            onChange={e => update('search', e.target.value)}
            placeholder="Search by title…"
            aria-label="Search opportunities by title"
            className="pl-9"
          />
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <SelectFilter
            label="Type"
            value={filters.type === 'All' ? ALL : filters.type}
            onValueChange={v =>
              update('type', (v === ALL ? 'All' : v) as OpportunityType | 'All')
            }
            options={[
              { value: ALL, label: 'All types' },
              ...TYPE_OPTIONS.map(t => ({ value: t, label: TYPE_META[t].label })),
            ]}
          />
          <SelectFilter
            label="Status"
            value={filters.status === 'All' ? ALL : filters.status}
            onValueChange={v =>
              update(
                'status',
                (v === ALL ? 'All' : v) as OpportunityStatus | 'All'
              )
            }
            options={[
              { value: ALL, label: 'All statuses' },
              ...STATUS_OPTIONS.map(s => ({
                value: s,
                label: STATUS_META[s].label,
              })),
            ]}
          />
          {sources.length > 0 && (
            <SelectFilter
              label="Source"
              value={filters.source === 'All' ? ALL : filters.source}
              onValueChange={v => update('source', v === ALL ? 'All' : v)}
              options={[
                { value: ALL, label: 'All sources' },
                ...sources.map(s => ({ value: s, label: s })),
              ]}
            />
          )}
          {allTags.length > 0 && (
            <SelectFilter
              label="Tag"
              value={filters.tag === 'All' ? ALL : filters.tag}
              onValueChange={v => update('tag', v === ALL ? 'All' : v)}
              options={[
                { value: ALL, label: 'All tags' },
                ...allTags.map(t => ({ value: t, label: t })),
              ]}
            />
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="kicker mr-1">due within</span>
          {DUE_WITHIN_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => update('dueWithin', opt.value)}
              aria-pressed={filters.dueWithin === opt.value}
              className={cn(
                'rounded-full border px-3 py-1 font-mono text-xs transition-colors',
                filters.dueWithin === opt.value
                  ? 'border-ink bg-ink text-paper'
                  : 'border-rule text-ink-muted hover:bg-muted'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-rule pt-3">
          <span className="font-mono text-xs text-ink-faint" aria-live="polite">
            {activeCount} of {totalCount} shown
          </span>

          <div className="flex items-center gap-2">
            <span className="kicker">sort by</span>
            <Select
              value={filters.sortKey}
              onValueChange={v => update('sortKey', v as SortKey)}
            >
              <SelectTrigger size="sm" className="h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(SORT_LABELS) as SortKey[]).map(key => (
                  <SelectItem key={key} value={key}>
                    {SORT_LABELS[key]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                update('sortDir', filters.sortDir === 'asc' ? 'desc' : 'asc')
              }
              aria-label={
                filters.sortDir === 'asc'
                  ? 'Sort ascending, switch to descending'
                  : 'Sort descending, switch to ascending'
              }
              className="h-8 font-mono text-xs"
            >
              {filters.sortDir === 'asc' ? '↑ Asc' : '↓ Desc'}
            </Button>
            {hasActiveFilters && (
              <Button
                size="sm"
                variant="ghost"
                onClick={clearFilters}
                className="h-8 text-xs text-accent"
              >
                Clear
              </Button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function SelectFilter({
  label,
  value,
  onValueChange,
  options,
}: {
  label: string;
  value: string;
  onValueChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="space-y-1">
      <span className="kicker">{label}</span>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger size="sm" className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map(o => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
