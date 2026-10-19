import { loadDataset, DatasetError } from './_lib/loadDataset.ts';
import { CACHE, datasetUnavailable, fail, json, requireGet, sendText } from './_lib/respond.ts';
import type { ApiRequest, ApiResponse, OpportunityRecord } from './_lib/types.ts';
import { ParamError, filterItems, parseListParams, sortItems } from './_lib/validate.ts';

/**
 * GET /api/export?format=csv|ics|json — server-side export of the filtered set (§11.4).
 * Honours the same filters as /api/opportunities (q, type, source, tag,
 * status=rolling, deadline_within, sort). ICS includes dated items only —
 * rolling (empty-deadline) items have no calendar date and are excluded,
 * noted via an X-WR-CALDESC suffix in the calendar description.
 */

const FORMATS = ['csv', 'ics', 'json'] as const;
type Format = (typeof FORMATS)[number];

function parseFormat(query: Record<string, unknown> | undefined): Format {
  const v = query?.format;
  const raw = (Array.isArray(v) ? v[0] : v)?.toString().trim().toLowerCase();
  if (raw === undefined || raw === '') return 'json';
  if ((FORMATS as readonly string[]).includes(raw)) return raw as Format;
  throw new ParamError(`format must be one of: ${FORMATS.join(', ')}.`);
}

const CSV_COLUMNS: Array<{ key: string; get: (i: OpportunityRecord) => string }> = [
  { key: 'id', get: (i) => i.id ?? i.fingerprint ?? '' },
  { key: 'title', get: (i) => i.title },
  { key: 'type', get: (i) => i.type },
  { key: 'source', get: (i) => i.source },
  { key: 'link', get: (i) => i.link },
  { key: 'deadline', get: (i) => i.deadline },
  { key: 'eligibility', get: (i) => i.eligibility ?? '' },
  { key: 'tags', get: (i) => (i.tags ?? []).join('; ') },
  { key: 'location', get: (i) => i.location ?? '' },
  { key: 'date_added', get: (i) => i.date_added },
];

/** Manual CSV quoting: wrap in quotes when the value contains comma, quote, or newline. */
function csvCell(value: string): string {
  if (/[",\r\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

function toCsv(items: OpportunityRecord[]): string {
  const header = CSV_COLUMNS.map((c) => c.key).join(',');
  const rows = items.map((item) => CSV_COLUMNS.map((c) => csvCell(c.get(item))).join(','));
  return [header, ...rows].join('\r\n');
}

function icsEscape(s: string): string {
  return s.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
}

/** Fold ICS lines at 75 octets per RFC 5545. */
function fold(line: string): string {
  if (line.length <= 75) return line;
  const parts: string[] = [];
  let rest = line;
  parts.push(rest.slice(0, 75));
  rest = rest.slice(75);
  while (rest.length > 74) {
    parts.push(` ${rest.slice(0, 74)}`);
    rest = rest.slice(74);
  }
  if (rest) parts.push(` ${rest}`);
  return parts.join('\r\n');
}

function toIcs(items: OpportunityRecord[], total: number): string {
  const dated = items.filter((i) => i.deadline !== '');
  const excluded = items.length - dated.length;
  const dtstamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
  const lines: string[] = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//OPP-Track//Opportunities//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    `X-WR-CALNAME:${icsEscape('OPP-Track — deadlines')}`,
    `X-WR-CALDESC:${icsEscape(
      `Dated opportunities from OPP-Track. ${excluded} of ${total} items are rolling/evergreen (no deadline) and are excluded from this calendar.`,
    )}`,
  ];
  for (const item of dated) {
    const id = item.id ?? item.fingerprint ?? '';
    const dtstart = item.deadline.replace(/-/g, '');
    const desc = [item.eligibility, item.source, item.link].filter(Boolean).join(' · ');
    lines.push(
      'BEGIN:VEVENT',
      fold(`UID:${icsEscape(id)}@opp-track`),
      `DTSTAMP:${dtstamp}`,
      `DTSTART;VALUE=DATE:${dtstart}`,
      fold(`SUMMARY:${icsEscape(item.title)}`),
      fold(`DESCRIPTION:${icsEscape(desc)}`),
      fold(`URL:${item.link}`),
      'END:VEVENT',
    );
  }
  lines.push('END:VCALENDAR');
  return lines.join('\r\n');
}

export default function handler(req: ApiRequest, res: ApiResponse): unknown {
  if (!requireGet(req, res)) return;
  try {
    const format = parseFormat(req.query);
    const params = parseListParams(req.query);
    const ds = loadDataset();
    const filtered = sortItems(filterItems(ds.items, params), params);

    if (format === 'csv') {
      sendText(res, 200, toCsv(filtered), {
        cache: CACHE.dataset,
        contentType: 'text/csv; charset=utf-8',
        disposition: 'attachment; filename="opportunities.csv"',
      });
      return;
    }
    if (format === 'ics') {
      sendText(res, 200, toIcs(filtered, filtered.length), {
        cache: CACHE.dataset,
        contentType: 'text/calendar; charset=utf-8',
        disposition: 'attachment; filename="opportunities.ics"',
      });
      return;
    }
    json(
      res,
      200,
      { items: filtered, page: params.page, page_size: params.pageSize, total: filtered.length, export_format: 'json' },
      { cache: CACHE.dataset },
    );
  } catch (err) {
    if (err instanceof ParamError) {
      fail(res, 400, err.code, err.message);
      return;
    }
    if (err instanceof DatasetError) {
      datasetUnavailable(res);
      return;
    }
    fail(res, 500, 'internal_error', 'Unexpected error.');
  }
}
