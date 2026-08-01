import { useMemo } from 'react';
import type { Opportunity, Filters, SortKey } from '../types/opportunity';
import { isExpiredOrCompleted, isWithinDays } from '../utils';

interface UseFiltersReturn {
  active: Opportunity[];
  archived: Opportunity[];
  sources: string[];
  allTags: string[];
  totalCount: number;
}

const SORTERS: Record<SortKey, (a: Opportunity, b: Opportunity) => number> = {
  deadline: (a, b) => a.deadline.localeCompare(b.deadline),
  date_added: (a, b) => a.date_added.localeCompare(b.date_added),
  title: (a, b) => a.title.localeCompare(b.title),
};

export function useFilters(opps: Opportunity[], filters: Filters): UseFiltersReturn {
  return useMemo(() => {
    let list = [...opps];

    if (filters.search) {
      const q = filters.search.toLowerCase();
      list = list.filter(o => o.title.toLowerCase().includes(q));
    }

    if (filters.type !== 'All') {
      list = list.filter(o => o.type === filters.type);
    }

    if (filters.status !== 'All') {
      list = list.filter(o => o.status === filters.status);
    }

    if (filters.source !== 'All') {
      list = list.filter(o => o.source === filters.source);
    }

    if (filters.tag !== 'All') {
      list = list.filter(o => o.tags.includes(filters.tag));
    }

    if (filters.dueWithin > 0) {
      list = list.filter(
        o => o.status !== 'Completed' && isWithinDays(o.deadline, filters.dueWithin)
      );
    }

    const dir = filters.sortDir === 'asc' ? 1 : -1;
    list.sort((a, b) => SORTERS[filters.sortKey](a, b) * dir);

    const active: Opportunity[] = [];
    const archived: Opportunity[] = [];

    for (const opp of list) {
      if (isExpiredOrCompleted(opp.deadline, opp.status)) {
        archived.push(opp);
      } else {
        active.push(opp);
      }
    }

    const sources = Array.from(
      new Set(opps.map(o => o.source).filter(Boolean))
    ).sort();

    const allTags = Array.from(
      new Set(opps.flatMap(o => o.tags).filter(Boolean))
    ).sort();

    return {
      active,
      archived,
      sources,
      allTags,
      totalCount: list.length,
    };
  }, [opps, filters]);
}
