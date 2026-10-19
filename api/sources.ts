import { readFileSync } from 'node:fs';
import path from 'node:path';
import { loadDataset, DatasetError } from './_lib/loadDataset.js';
import { CACHE, datasetUnavailable, fail, json, requireGet } from './_lib/respond.js';
import type { ApiRequest, ApiResponse } from './_lib/types.js';

interface HealthEntry {
  source: string;
  items?: number;
  time_s?: number;
  status?: string;
}

/**
 * GET /api/sources — source registry (counts from the dataset) + health map
 * from data/scraper_health.json (§11.4). Degrades gracefully when the health
 * file is absent (health: null).
 */
export default function handler(req: ApiRequest, res: ApiResponse): unknown {
  if (!requireGet(req, res)) return;
  try {
    const ds = loadDataset();
    const counts = new Map<string, number>();
    for (const item of ds.items) {
      counts.set(item.source, (counts.get(item.source) ?? 0) + 1);
    }
    const sources = [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([source, item_count]) => ({ source, item_count }));

    let health: Record<string, { status: string; items: number | null; time_s: number | null }> | null = null;
    try {
      const raw = readFileSync(path.join(process.cwd(), 'data', 'scraper_health.json'));
      const parsed = JSON.parse(raw.toString('utf8')) as HealthEntry[];
      if (Array.isArray(parsed)) {
        health = {};
        for (const entry of parsed) {
          if (!entry || typeof entry.source !== 'string') continue;
          health[entry.source] = {
            status: typeof entry.status === 'string' ? entry.status : 'UNKNOWN',
            items: typeof entry.items === 'number' ? entry.items : null,
            time_s: typeof entry.time_s === 'number' ? entry.time_s : null,
          };
        }
      }
    } catch {
      // health file absent or unreadable — degrade to null
    }

    json(res, 200, { sources, health }, { cache: CACHE.dataset });
  } catch (err) {
    if (err instanceof DatasetError) {
      datasetUnavailable(res);
      return;
    }
    fail(res, 500, 'internal_error', 'Unexpected error.');
  }
}
