import { loadDataset, DatasetError } from '../_lib/loadDataset.js';
import { applyEdit, loadEdits, recordId } from '../_lib/edits.js';
import { CACHE, datasetUnavailable, fail, json, requireGet } from '../_lib/respond.js';
import type { ApiRequest, ApiResponse } from '../_lib/types.js';
import { ParamError } from '../_lib/validate.js';

/**
 * GET /api/opportunities/:id — single record by stable id (fingerprint hash, §11.2).
 * 404 `{error, code:'not_found'}` otherwise (§11.4).
 * Any stored user edit is merged over the record before it is returned.
 */
export default async function handler(req: ApiRequest, res: ApiResponse): Promise<unknown> {
  if (!requireGet(req, res)) return;
  try {
    const raw = req.query?.id;
    const id = (Array.isArray(raw) ? raw[0] : raw)?.trim();
    if (!id) throw new ParamError('id is required.');
    if (id.length > 128) throw new ParamError('id is too long.');
    const ds = loadDataset();
    const found = ds.items.find((it) => recordId(it) === id);
    if (!found) {
      fail(res, 404, 'not_found', 'No opportunity with that id.', { cache: CACHE.record });
      return;
    }
    const edits = await loadEdits();
    json(res, 200, applyEdit(found, edits.edits[id]), { cache: CACHE.record });
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
