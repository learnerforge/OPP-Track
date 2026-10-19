import { loadDataset, DatasetError } from './_lib/loadDataset.ts';
import { CACHE, datasetUnavailable, fail, json, requireGet } from './_lib/respond.ts';
import type { ApiRequest, ApiResponse } from './_lib/types.ts';
import { ParamError, filterItems, parseListParams, sortItems } from './_lib/validate.ts';

/**
 * GET /api/opportunities — filtered + paginated reads over the full dataset (§11.4).
 * Params: q, type, source, tag, status=rolling, deadline_within (days), sort, page, page_size.
 * Returns {items, page, page_size, total, total_pages}.
 */
export default function handler(req: ApiRequest, res: ApiResponse): unknown {
  if (!requireGet(req, res)) return;
  try {
    const params = parseListParams(req.query);
    const ds = loadDataset();
    const filtered = sortItems(filterItems(ds.items, params), params);
    const total = filtered.length;
    const total_pages = Math.max(1, Math.ceil(total / params.pageSize));
    const start = (params.page - 1) * params.pageSize;
    const items = filtered.slice(start, start + params.pageSize);
    json(res, 200, { items, page: params.page, page_size: params.pageSize, total, total_pages }, {
      cache: CACHE.dataset,
    });
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
