import type { OpportunityRecord } from './types.ts';

/** Query-param validation mirroring the data validator's rules (§11.4). */
export const OPPORTUNITY_TYPES = ['Hackathon', 'Internship', 'Certification', 'Competition'] as const;
export const SORTS = ['deadline_asc', 'deadline_desc', 'relevance'] as const;

export class ParamError extends Error {
  readonly code = 'invalid_param';
  constructor(message: string) {
    super(message);
    this.name = 'ParamError';
  }
}

export interface ListParams {
  q?: string;
  type?: (typeof OPPORTUNITY_TYPES)[number];
  source?: string;
  tag?: string;
  rolling?: boolean;
  deadlineWithinDays?: number;
  sort: (typeof SORTS)[number];
  page: number;
  pageSize: number;
}

type Query = Record<string, string | string[] | undefined> | undefined;

function first(query: Query, key: string): string | undefined {
  const v = query?.[key];
  const s = Array.isArray(v) ? v[0] : v;
  if (typeof s !== 'string') return undefined;
  const t = s.trim();
  return t === '' ? undefined : t;
}

/** page_size: int 1..100, default 50. */
export function parsePageSize(query: Query): number {
  const raw = first(query, 'page_size');
  if (raw === undefined) return 50;
  if (!/^\d+$/.test(raw)) throw new ParamError('page_size must be an integer between 1 and 100.');
  const n = Number(raw);
  if (n < 1 || n > 100) throw new ParamError('page_size must be an integer between 1 and 100.');
  return n;
}

/** page: integer >= 1, default 1. */
export function parsePage(query: Query): number {
  const raw = first(query, 'page');
  if (raw === undefined) return 1;
  if (!/^\d+$/.test(raw)) throw new ParamError('page must be an integer >= 1.');
  const n = Number(raw);
  if (n < 1) throw new ParamError('page must be an integer >= 1.');
  return n;
}

export function parseType(query: Query): ListParams['type'] {
  const raw = first(query, 'type');
  if (raw === undefined) return undefined;
  if (!(OPPORTUNITY_TYPES as readonly string[]).includes(raw)) {
    throw new ParamError(`type must be one of: ${OPPORTUNITY_TYPES.join(', ')}.`);
  }
  return raw as ListParams['type'];
}

/** status: only `rolling` is meaningful server-side (empty deadline). */
export function parseStatus(query: Query): boolean {
  const raw = first(query, 'status');
  if (raw === undefined) return false;
  if (raw !== 'rolling') throw new ParamError('status must be "rolling" when provided.');
  return true;
}

/** q: trimmed, capped at 200 chars. */
export function parseSearch(query: Query): string | undefined {
  const raw = first(query, 'q');
  if (raw === undefined) return undefined;
  if (raw.length > 200) throw new ParamError('q must be 200 characters or fewer.');
  return raw;
}

/** deadline_within: positive integer number of days, 1..365. */
export function parseDeadlineWithin(query: Query): number | undefined {
  const raw = first(query, 'deadline_within');
  if (raw === undefined) return undefined;
  if (!/^\d+$/.test(raw)) throw new ParamError('deadline_within must be an integer number of days (1-365).');
  const n = Number(raw);
  if (n < 1 || n > 365) throw new ParamError('deadline_within must be between 1 and 365 days.');
  return n;
}

export function parseSort(query: Query): ListParams['sort'] {
  const raw = first(query, 'sort');
  if (raw === undefined) return 'deadline_asc';
  if (!(SORTS as readonly string[]).includes(raw)) {
    throw new ParamError(`sort must be one of: ${SORTS.join(', ')}.`);
  }
  return raw as ListParams['sort'];
}

/** YYYY-MM-DD or empty/absent. */
export function parseDate(value: string | undefined, field: string): string | undefined {
  if (value === undefined || value === '') return undefined;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new ParamError(`${field} must be in YYYY-MM-DD format.`);
  }
  return value;
}

/** Parse the shared filter set used by /api/opportunities and /api/export. */
export function parseListParams(query: Query): ListParams {
  return {
    q: parseSearch(query),
    type: parseType(query),
    source: first(query, 'source'),
    tag: first(query, 'tag'),
    rolling: parseStatus(query),
    deadlineWithinDays: parseDeadlineWithin(query),
    sort: parseSort(query),
    page: parsePage(query),
    pageSize: parsePageSize(query),
  };
}

const DAY_MS = 86_400_000;

/** Days from today until deadline (ISO date string); negative = past. */
export function daysUntil(deadline: string, now: Date): number {
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const target = Date.parse(`${deadline}T00:00:00Z`);
  return Math.round((target - today) / DAY_MS);
}

/** Apply the filter set. Rolling = empty deadline. */
export function filterItems(
  items: OpportunityRecord[],
  params: ListParams,
  now: Date = new Date(),
): OpportunityRecord[] {
  const q = params.q?.toLowerCase();
  return items.filter((item) => {
    if (params.rolling && item.deadline !== '') return false;
    if (!params.rolling && params.type && item.type !== params.type) return false;
    if (params.source && item.source.toLowerCase() !== params.source.toLowerCase()) return false;
    if (params.tag && !(item.tags ?? []).some((t) => t.toLowerCase() === params.tag!.toLowerCase())) return false;
    if (params.deadlineWithinDays !== undefined) {
      if (item.deadline === '') return false;
      const d = daysUntil(item.deadline, now);
      if (d < 0 || d > params.deadlineWithinDays) return false;
    }
    if (q) {
      const hay = `${item.title} ${item.source} ${item.eligibility ?? ''} ${(item.tags ?? []).join(' ')}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

/** Sort a copy. Rolling items always sort after dated ones within each group. */
export function sortItems(items: OpportunityRecord[], params: ListParams): OpportunityRecord[] {
  const dir = params.sort === 'deadline_desc' ? -1 : 1;
  const relevance = params.sort === 'relevance';
  const q = params.q?.toLowerCase();
  const scored = items.map((item) => ({
    item,
    score: relevance && q ? relevanceScore(item, q) : 0,
  }));
  scored.sort((a, b) => {
    if (relevance && q && a.score !== b.score) return a.score - b.score;
    const ad = a.item.deadline === '' ? 1 : 0;
    const bd = b.item.deadline === '' ? 1 : 0;
    if (ad !== bd) return ad - bd;
    if (a.item.deadline !== b.item.deadline) {
      return a.item.deadline < b.item.deadline ? -dir : dir;
    }
    return a.item.title.localeCompare(b.item.title);
  });
  return scored.map((s) => s.item);
}

/** Lower rank = better match: title > tags > source > other. */
function relevanceScore(item: OpportunityRecord, q: string): number {
  const title = item.title.toLowerCase();
  if (title === q) return 0;
  if (title.startsWith(q)) return 1;
  if (title.includes(q)) return 2;
  if ((item.tags ?? []).some((t) => t.toLowerCase().includes(q))) return 3;
  if (item.source.toLowerCase().includes(q)) return 4;
  return 5;
}
