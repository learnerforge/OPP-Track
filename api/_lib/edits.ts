import type { OpportunityRecord } from './types.js';

/**
 * Shared edit overrides, stored as a single JSON document in Vercel Blob.
 *
 * The scraped dataset is read-only JSON in the repo — the pipeline overwrites
 * it every 8 hours. User edits therefore live *beside* it, keyed by the
 * opportunity's stable identity, and are merged over the catalog at read time.
 * A published scrape never destroys them, which is the whole point.
 *
 * Storage shape (one blob, `edits/catalog-edits.json`):
 *
 *   {
 *     "version": 1,
 *     "updated_at": "2026-10-21T…Z",
 *     "edits": {
 *       "<id>": { "fields": {...}, "updated_at": "...", "updated_by": "learnerforge" }
 *     }
 *   }
 *
 * Access is via `@vercel/blob` using the `BLOB_READ_WRITE_TOKEN` environment
 * variable (set in Vercel, never committed). When the token is absent the
 * module degrades to an empty, non-writable store so local dev and any
 * deployment without Blob configured still serves the catalog correctly.
 */

export const EDITS_BLOB_PATH = 'edits/catalog-edits.json';

/** Field names a user is allowed to edit. Anything else is rejected. */
export const EDITABLE_FIELDS = [
  'title',
  'type',
  'link',
  'deadline',
  'location',
  'prize_pool',
  'eligibility',
  'notes',
] as const;

export type EditableField = (typeof EDITABLE_FIELDS)[number];

/** One stored override for one opportunity. */
export interface StoredEdit {
  fields: Partial<Record<EditableField, string>>;
  updated_at: string;
  updated_by: string;
}

/** The whole shared document. */
export interface EditDocument {
  version: number;
  updated_at: string;
  edits: Record<string, StoredEdit>;
}

export class EditsError extends Error {
  readonly code: string;
  constructor(message: string, code = 'edits_unavailable') {
    super(message);
    this.name = 'EditsError';
    this.code = code;
  }
}

/** True when Blob credentials are configured for this deployment. */
export function blobConfigured(): boolean {
  return Boolean(process.env.BLOB_READ_WRITE_TOKEN);
}

const EMPTY: EditDocument = { version: 1, updated_at: '', edits: {} };

/** Module-scope cache so a warm lambda does not refetch per request. */
let cache: { doc: EditDocument; at: number } | null = null;
const CACHE_MS = 15_000;

/** Drop the in-process cache (after a write, so the next read sees it). */
export function invalidateEditsCache(): void {
  cache = null;
}

/**
 * Read the shared edit document.
 *
 * Never throws for a *missing* blob — that is the normal first-run state and
 * yields an empty document. A genuine transport/auth failure also degrades to
 * empty so that a Blob outage cannot take the catalog read path down with it.
 */
export async function loadEdits(): Promise<EditDocument> {
  if (cache && Date.now() - cache.at < CACHE_MS) return cache.doc;
  if (!blobConfigured()) return EMPTY;

  try {
    const { list } = await import('@vercel/blob');
    const { blobs } = await list({ prefix: EDITS_BLOB_PATH, limit: 1 });
    const match = blobs.find((b) => b.pathname === EDITS_BLOB_PATH);
    if (!match) {
      cache = { doc: EMPTY, at: Date.now() };
      return EMPTY;
    }
    const res = await fetch(match.url, { cache: 'no-store' });
    if (!res.ok) throw new EditsError(`blob fetch failed (${res.status})`);
    const parsed = (await res.json()) as Partial<EditDocument>;
    const doc: EditDocument = {
      version: typeof parsed.version === 'number' ? parsed.version : 1,
      updated_at: typeof parsed.updated_at === 'string' ? parsed.updated_at : '',
      edits:
        parsed.edits && typeof parsed.edits === 'object'
          ? (parsed.edits as Record<string, StoredEdit>)
          : {},
    };
    cache = { doc, at: Date.now() };
    return doc;
  } catch {
    // Degrade rather than fail the read path.
    return EMPTY;
  }
}

/**
 * Read an edit document to use as a write baseline.
 *
 * Read endpoints may degrade to an empty overlay during a Blob outage. A save
 * must not: writing that empty overlay back would erase all prior edits.
 */
async function loadEditsForWrite(): Promise<EditDocument> {
  if (!blobConfigured()) {
    throw new EditsError(
      'Edit storage is not configured (BLOB_READ_WRITE_TOKEN is unset).',
      'edits_not_configured',
    );
  }

  try {
    const { list } = await import('@vercel/blob');
    const { blobs } = await list({ prefix: EDITS_BLOB_PATH, limit: 1 });
    const match = blobs.find((b) => b.pathname === EDITS_BLOB_PATH);
    if (!match) return EMPTY;
    const res = await fetch(match.url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`blob fetch failed (${res.status})`);
    const parsed = (await res.json()) as Partial<EditDocument>;
    if (parsed.edits !== undefined && (!parsed.edits || typeof parsed.edits !== 'object')) {
      throw new Error('blob document has an invalid edits field');
    }
    return {
      version: typeof parsed.version === 'number' ? parsed.version : 1,
      updated_at: typeof parsed.updated_at === 'string' ? parsed.updated_at : '',
      edits: (parsed.edits as Record<string, StoredEdit> | undefined) ?? {},
    };
  } catch (err) {
    throw new EditsError(
      `Could not read existing edits before saving: ${String((err as Error)?.message ?? err)}`,
    );
  }
}

/**
 * Persist a single edit and return the full updated document.
 *
 * Read-modify-write against one blob. Two simultaneous editors can therefore
 * lose one update; for a single-admin tool that is an acceptable trade-off
 * against the cost of a real transactional store, and it is called out here so
 * the limitation is explicit rather than discovered later.
 */
export async function saveEdit(
  id: string,
  fields: Partial<Record<EditableField, string>>,
  updatedBy: string,
): Promise<EditDocument> {
  if (!blobConfigured()) {
    throw new EditsError(
      'Edit storage is not configured (BLOB_READ_WRITE_TOKEN is unset).',
      'edits_not_configured',
    );
  }

  const { put } = await import('@vercel/blob');
  const current = await loadEditsForWrite();
  const now = new Date().toISOString();

  const next: EditDocument = {
    version: current.version || 1,
    updated_at: now,
    edits: {
      ...current.edits,
      [id]: {
        fields: { ...(current.edits[id]?.fields ?? {}), ...fields },
        updated_at: now,
        updated_by: updatedBy,
      },
    },
  };

  await put(EDITS_BLOB_PATH, JSON.stringify(next, null, 2), {
    access: 'public',
    contentType: 'application/json',
    addRandomSuffix: false,
    allowOverwrite: true,
  });

  cache = { doc: next, at: Date.now() };
  return next;
}

/**
 * Apply stored edits over a record, returning a new object.
 *
 * Only fields the user is allowed to change are applied, so a stale or
 * hand-crafted document can never inject arbitrary keys into the API output.
 */
export function applyEdit<T extends OpportunityRecord>(
  item: T,
  edit: StoredEdit | undefined,
): T {
  if (!edit || !edit.fields) return item;
  const merged: OpportunityRecord = { ...item };
  for (const field of EDITABLE_FIELDS) {
    const value = edit.fields[field];
    if (typeof value === 'string') merged[field] = value;
  }
  merged.edited = true;
  merged.edited_at = edit.updated_at;
  return merged as T;
}

/** Identity of a record, matching /api/opportunities/[id] and the app. */
export function recordId(item: OpportunityRecord): string {
  return item.id ?? item.fingerprint ?? '';
}

/**
 * Apply every stored edit over a list of records.
 *
 * Used by the read endpoints so an edit is visible everywhere the catalog is
 * served, not only inside the edit UI. Returns the original array untouched
 * (same references) when there are no edits at all.
 */
export function applyEdits<T extends OpportunityRecord>(
  items: T[],
  doc: EditDocument,
): T[] {
  const map = doc?.edits;
  if (!map || Object.keys(map).length === 0) return items;
  return items.map((item) => {
    const id = recordId(item);
    const edit = id ? map[id] : undefined;
    return edit ? applyEdit(item, edit) : item;
  });
}
