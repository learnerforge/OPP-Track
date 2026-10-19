import { createHash } from 'node:crypto';
import { readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import type { OpportunityRecord } from './types.js';

/**
 * Dataset access. Reads `data/scraped_opportunities.json` once per cold start
 * and caches in module scope. Also exposes `loadManifest()` reading
 * `data/manifest.json` (written by the publish pipeline, companion E3);
 * when absent it degrades by deriving sha256 + count from the canonical file.
 * Paths resolve from `process.cwd()` (repo root on Vercel).
 */

export class DatasetError extends Error {
  constructor() {
    super('dataset unavailable');
    this.name = 'DatasetError';
  }
}

export interface Dataset {
  items: OpportunityRecord[];
  sha256: string;
  mtime: Date;
}

let datasetCache: Dataset | null = null;

export function loadDataset(): Dataset {
  if (datasetCache) return datasetCache;
  const file = path.join(process.cwd(), 'data', 'scraped_opportunities.json');
  let raw: Buffer;
  let mtime: Date;
  try {
    raw = readFileSync(file);
    mtime = statSync(file).mtime;
  } catch {
    throw new DatasetError();
  }
  let items: unknown;
  try {
    items = JSON.parse(raw.toString('utf8'));
  } catch {
    throw new DatasetError();
  }
  if (!Array.isArray(items)) throw new DatasetError();
  datasetCache = {
    items: items as OpportunityRecord[],
    sha256: createHash('sha256').update(raw).digest('hex'),
    mtime,
  };
  return datasetCache;
}

export interface Manifest {
  sha256: string;
  sha8: string;
  item_count: number;
  generated_at: string;
  /** 'manifest' when data/manifest.json existed, 'derived' when recomputed on the fly. */
  origin: 'manifest' | 'derived';
}

let manifestCache: Manifest | null = null;

export function loadManifest(): Manifest {
  if (manifestCache) return manifestCache;
  const ds = loadDataset();
  const derived: Manifest = {
    sha256: ds.sha256,
    sha8: ds.sha256.slice(0, 8),
    item_count: ds.items.length,
    generated_at: ds.mtime.toISOString(),
    origin: 'derived',
  };
  try {
    const file = path.join(process.cwd(), 'data', 'manifest.json');
    const raw = readFileSync(file);
    const stat = statSync(file);
    const parsed = JSON.parse(raw.toString('utf8')) as Partial<Manifest>;
    if (typeof parsed.sha256 === 'string' && typeof parsed.item_count === 'number') {
      manifestCache = {
        sha256: parsed.sha256,
        sha8: parsed.sha256.slice(0, 8),
        item_count: parsed.item_count,
        generated_at:
          typeof parsed.generated_at === 'string' && parsed.generated_at
            ? parsed.generated_at
            : stat.mtime.toISOString(),
        origin: 'manifest',
      };
    }
  } catch {
    // degrade to derived
  }
  manifestCache ??= derived;
  return manifestCache;
}
