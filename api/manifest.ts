import { loadManifest, DatasetError } from './_lib/loadDataset.ts';
import { CACHE, datasetUnavailable, fail, json, requireGet } from './_lib/respond.ts';
import type { ApiRequest, ApiResponse } from './_lib/types.ts';

/**
 * GET /api/manifest — the manifest, CORS-enabled for the app (§11.4).
 * Serves data/manifest.json when the pipeline has published one, otherwise
 * derives {sha256, sha8, item_count, generated_at} from the canonical file.
 */
export default function handler(req: ApiRequest, res: ApiResponse): unknown {
  if (!requireGet(req, res)) return;
  try {
    const man = loadManifest();
    json(res, 200, man, { cache: CACHE.manifest, cors: true });
  } catch (err) {
    if (err instanceof DatasetError) {
      datasetUnavailable(res);
      return;
    }
    fail(res, 500, 'internal_error', 'Unexpected error.');
  }
}
