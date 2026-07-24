import { useMemo } from 'react';
import type { Opportunity, Filters } from '../types/opportunity';
import { isExpiredOrCompleted } from '../utils';

interface UseFiltersReturn {
  active: Opportunity[];
  archived: Opportunity[];
  sources: string[];
  allTags: string[];
  totalCount: number;
}

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

    const active: Opportunity[] = [];
    const archived: Opportunity[] = [];

    for (const opp of list) {
      if (isExpiredOrCompleted(opp.deadline, opp.status)) {
        archived.push(opp);
      } else {
        active.push(opp);
      }
    }

    active.sort((a, b) => a.deadline.localeCompare(b.deadline));
    archived.sort((a, b) => b.deadline.localeCompare(a.deadline));

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
