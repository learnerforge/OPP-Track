import { readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { CACHE, datasetUnavailable, fail, json, requireGet } from './_lib/respond.ts';
import { DatasetError } from './_lib/loadDataset.ts';
import type { ApiRequest, ApiResponse } from './_lib/types.ts';

/**
 * GET /api/report/latest — newest data/reports/publish-*.md as JSON
 * `{filename, generated_at, body}` (§11.4). 404 `{error, code:'not_found'}`
 * when no report has been published yet.
 */
export default function handler(req: ApiRequest, res: ApiResponse): unknown {
  if (!requireGet(req, res)) return;
  try {
    const dir = path.join(process.cwd(), 'data', 'reports');
    let files: string[];
    try {
      files = readdirSync(dir).filter((f) => /^publish-[\w.-]+\.md$/i.test(f));
    } catch {
      files = [];
    }
    if (files.length === 0) {
      fail(res, 404, 'not_found', 'No publish report has been published yet.', { cache: CACHE.report });
      return;
    }
    // Filenames sort chronologically (publish-YYYYMMDD...); pick the greatest.
    files.sort();
    const filename = files[files.length - 1];
    const full = path.join(dir, filename);
    const body = readFileSync(full, 'utf8');
    const generated_at = statSync(full).mtime.toISOString();
    json(res, 200, { filename, generated_at, body }, { cache: CACHE.report });
  } catch (err) {
    if (err instanceof DatasetError) {
      datasetUnavailable(res);
      return;
    }
    fail(res, 500, 'internal_error', 'Unexpected error.');
  }
}
