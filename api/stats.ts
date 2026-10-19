import { loadDataset, DatasetError } from './_lib/loadDataset.js';
import { CACHE, datasetUnavailable, fail, json, requireGet } from './_lib/respond.js';
import type { ApiRequest, ApiResponse } from './_lib/types.js';
import { daysUntil } from './_lib/validate.js';

/**
 * GET /api/stats — type/source histograms, rolling vs dated, closing-soon (≤7 days) (§11.4).
 */
export default function handler(req: ApiRequest, res: ApiResponse): unknown {
  if (!requireGet(req, res)) return;
  try {
    const ds = loadDataset();
    const now = new Date();
    const by_type: Record<string, number> = {};
    const by_source: Record<string, number> = {};
    let rolling = 0;
    let dated = 0;
    let closing_soon_7d = 0;
    for (const item of ds.items) {
      by_type[item.type] = (by_type[item.type] ?? 0) + 1;
      by_source[item.source] = (by_source[item.source] ?? 0) + 1;
      if (item.deadline === '') {
        rolling += 1;
        continue;
      }
      dated += 1;
      const d = daysUntil(item.deadline, now);
      if (d >= 0 && d <= 7) closing_soon_7d += 1;
    }
    json(
      res,
      200,
      {
        total: ds.items.length,
        by_type,
        by_source,
        rolling,
        dated,
        closing_soon_7d,
      },
      { cache: CACHE.dataset },
    );
  } catch (err) {
    if (err instanceof DatasetError) {
      datasetUnavailable(res);
      return;
    }
    fail(res, 500, 'internal_error', 'Unexpected error.');
  }
}
