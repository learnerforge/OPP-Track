import type { ApiRequest, ApiResponse } from './types.ts';

/**
 * Cache-Control values per §11.4 of fullstack.md.
 * Routes set their own Cache-Control; vercel.json only adds /data/* static rules.
 */
export const CACHE = {
  /** /api/health — freshness smoke, never cached. */
  health: 'no-store',
  /** /api/manifest — same manifest the app polls first. */
  manifest: 'public, s-maxage=300, stale-while-revalidate=86400',
  /** /api/report/latest — ops trail, short cache. */
  report: 'public, s-maxage=300',
  /** /api/opportunities, /api/stats, /api/sources, /api/export. */
  dataset: 'public, s-maxage=3600, stale-while-revalidate=86400',
  /** /api/opportunities/[id] — single record, no SWR needed but harmless. */
  record: 'public, s-maxage=3600',
  /** /api/og — derived image, cache a day. */
  og: 'public, s-maxage=86400',
} as const;

const CORS_HEADERS: Record<string, string> = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};

export function applyCors(res: ApiResponse): void {
  for (const [k, v] of Object.entries(CORS_HEADERS)) res.setHeader(k, v);
}

/** JSON response with cache headers. CORS is opt-in (only /api/manifest per §11.4). */
export function json(
  res: ApiResponse,
  status: number,
  body: unknown,
  opts: { cache?: string; cors?: boolean } = {},
): void {
  res.status(status);
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  if (opts.cache) res.setHeader('Cache-Control', opts.cache);
  if (opts.cors) applyCors(res);
  res.json(body);
}

/** Error envelope `{error, code}` per §11.4 conventions. */
export function fail(
  res: ApiResponse,
  status: number,
  code: string,
  error: string,
  opts: { cache?: string; cors?: boolean } = {},
): void {
  json(res, status, { error, code }, { ...opts, cache: opts.cache ?? CACHE.health });
}

/**
 * GET-only guard. §11.4: any other method → 405 `{error, code:'method_not_allowed'}`.
 * HEAD is treated as a read-only alias of GET (it must never hit a write path,
 * and there are none); everything else 405s. Returns true when the request may proceed.
 */
export function requireGet(req: ApiRequest, res: ApiResponse): boolean {
  const m = (req.method ?? 'GET').toUpperCase();
  if (m === 'GET' || m === 'HEAD') return true;
  res.setHeader('Allow', 'GET, HEAD');
  fail(res, 405, 'method_not_allowed', `Method ${m} is not allowed; this API is read-only.`);
  return false;
}

/** Dataset failed to load (missing file, bad JSON). Never leaks filesystem paths. */
export function datasetUnavailable(res: ApiResponse): void {
  fail(res, 503, 'dataset_unavailable', 'The dataset is not available right now. Try again after the next publish.');
}

/** Plain-text (non-JSON) response, e.g. CSV/ICS exports. */
export function sendText(
  res: ApiResponse,
  status: number,
  body: string,
  opts: { cache?: string; contentType: string; disposition?: string } = { contentType: 'text/plain; charset=utf-8' },
): void {
  res.status(status);
  res.setHeader('Content-Type', opts.contentType);
  if (opts.cache) res.setHeader('Cache-Control', opts.cache);
  if (opts.disposition) res.setHeader('Content-Disposition', opts.disposition);
  res.send(body);
}
