import { loadDataset, loadManifest, DatasetError } from './_lib/loadDataset.ts';
import { CACHE, datasetUnavailable, fail, json, requireGet } from './_lib/respond.ts';
import type { ApiRequest, ApiResponse } from './_lib/types.ts';

/**
 * GET /api/health — deploy + data-freshness smoke (§11.4).
 * `{ok, item_count, sha256, published_sha8, generated_at, age_hours, fresh}` — no-store.
 */
export default function handler(req: ApiRequest, res: ApiResponse): unknown {
  if (!requireGet(req, res)) return;
  try {
    const ds = loadDataset();
    const man = loadManifest();
    const ageHours = Math.max(0, (Date.now() - Date.parse(man.generated_at)) / 3_600_000);
    json(
      res,
      200,
      {
        ok: true,
        item_count: ds.items.length,
        sha256: ds.sha256,
        published_sha8: man.sha8,
        generated_at: man.generated_at,
        age_hours: Number(ageHours.toFixed(2)),
        fresh: ageHours < 12,
      },
      { cache: CACHE.health },
    );
  } catch (err) {
    if (err instanceof DatasetError) {
      datasetUnavailable(res);
      return;
    }
    fail(res, 500, 'internal_error', 'Unexpected error.');
  }
}
