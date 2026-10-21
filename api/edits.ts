import { loadDataset, DatasetError } from './_lib/loadDataset.js';
import {
  EDITABLE_FIELDS,
  EditsError,
  applyEdit,
  blobConfigured,
  loadEdits,
  recordId,
  saveEdit,
  type EditableField,
} from './_lib/edits.js';
import { CACHE, fail, json } from './_lib/respond.js';
import type { ApiRequest, ApiResponse } from './_lib/types.js';
import { OPPORTUNITY_TYPES, ParamError } from './_lib/validate.js';

/**
 * /api/edits — the shared edit store for opportunities.
 *
 *   GET  → { edits: { <id>: {fields, updated_at, updated_by} }, configured }
 *   POST → body { id, fields } ; validates, writes the override, echoes it back.
 *
 * This is the ONLY write path in the API. Every other route is read-only by
 * design (`requireGet`), and the scraped dataset itself is never modified —
 * edits are stored beside it and merged over it at read time.
 *
 * Auth: the shared secret in `EDITS_TOKEN` (set as a Vercel env var). The app
 * gates the edit UI behind its login screen, but a UI gate is not an access
 * control, so the write endpoint independently requires the same secret in the
 * `x-edits-token` header. When `EDITS_TOKEN` is unset the write path is closed
 * (503) rather than open — failing closed, never silently world-writable.
 */

const MAX_FIELD_LENGTH = 500;

/** Constant-time-ish comparison so a token check does not leak by timing. */
function tokenMatches(provided: string, expected: string): boolean {
  if (provided.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < provided.length; i++) {
    diff |= provided.charCodeAt(i) ^ expected.charCodeAt(i);
  }
  return diff === 0;
}

function header(req: ApiRequest, name: string): string {
  const raw = req.headers?.[name] ?? req.headers?.[name.toLowerCase()];
  return (Array.isArray(raw) ? raw[0] : raw) ?? '';
}

/** Validate and normalise the posted fields. Throws ParamError on bad input. */
function parseFields(input: unknown): Partial<Record<EditableField, string>> {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new ParamError('fields must be an object.');
  }
  const raw = input as Record<string, unknown>;
  const out: Partial<Record<EditableField, string>> = {};

  for (const key of Object.keys(raw)) {
    if (!(EDITABLE_FIELDS as readonly string[]).includes(key)) {
      throw new ParamError(`field '${key}' is not editable.`);
    }
  }
  for (const field of EDITABLE_FIELDS) {
    if (!(field in raw)) continue;
    const value = raw[field];
    if (typeof value !== 'string') throw new ParamError(`field '${field}' must be a string.`);
    const trimmed = value.trim();
    if (trimmed.length > MAX_FIELD_LENGTH) {
      throw new ParamError(`field '${field}' must be ${MAX_FIELD_LENGTH} characters or fewer.`);
    }
    if (field === 'deadline' && trimmed !== '' && !/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
      throw new ParamError('deadline must be YYYY-MM-DD or empty.');
    }
    if (field === 'type' && !(OPPORTUNITY_TYPES as readonly string[]).includes(trimmed)) {
      throw new ParamError(`type must be one of: ${OPPORTUNITY_TYPES.join(', ')}.`);
    }
    if (field === 'link' && trimmed !== '' && !/^https?:\/\/\S+$/i.test(trimmed)) {
      throw new ParamError('link must be an http(s) URL or empty.');
    }
    if (field === 'title' && trimmed === '') {
      throw new ParamError('title cannot be empty.');
    }
    out[field] = trimmed;
  }

  if (Object.keys(out).length === 0) throw new ParamError('no editable fields were provided.');
  return out;
}

export default async function handler(req: ApiRequest, res: ApiResponse): Promise<unknown> {
  const method = (req.method ?? 'GET').toUpperCase();

  try {
    if (method === 'GET' || method === 'HEAD') {
      const doc = await loadEdits();
      json(res, 200, { edits: doc.edits, updated_at: doc.updated_at, configured: blobConfigured() }, {
        cache: CACHE.health,
      });
      return;
    }

    if (method !== 'POST') {
      res.setHeader('Allow', 'GET, HEAD, POST');
      fail(res, 405, 'method_not_allowed', `Method ${method} is not allowed.`);
      return;
    }

    // Fail closed when the write secret is not configured.
    const expected = process.env.EDITS_TOKEN;
    if (!expected) {
      fail(res, 503, 'edits_not_configured', 'Edit storage is not configured on this deployment.');
      return;
    }
    if (!tokenMatches(header(req, 'x-edits-token'), expected)) {
      fail(res, 401, 'unauthorized', 'A valid edit token is required.');
      return;
    }

    const body = (req.body ?? {}) as Record<string, unknown>;
    const id = typeof body.id === 'string' ? body.id.trim() : '';
    if (!id) throw new ParamError('id is required.');
    if (id.length > 128) throw new ParamError('id is too long.');

    // The id must name a real opportunity: this stops the store being used as
    // arbitrary blob space by anyone who has the token.
    const ds = loadDataset();
    const target = ds.items.find((it) => recordId(it) === id);
    if (!target) {
      fail(res, 404, 'not_found', 'No opportunity with that id.');
      return;
    }

    const fields = parseFields(body.fields);
    const updatedBy = typeof body.updated_by === 'string' ? body.updated_by.slice(0, 64) : 'unknown';
    const doc = await saveEdit(id, fields, updatedBy);

    json(res, 200, {
      ok: true,
      id,
      edit: doc.edits[id],
      item: applyEdit(target, doc.edits[id]),
    }, { cache: CACHE.health });
  } catch (err) {
    if (err instanceof ParamError) {
      fail(res, 400, err.code, err.message);
      return;
    }
    if (err instanceof EditsError) {
      const status = err.code === 'edits_not_configured' ? 503 : 502;
      fail(res, status, err.code, err.message);
      return;
    }
    if (err instanceof DatasetError) {
      fail(res, 503, 'dataset_unavailable', 'The dataset is not available right now.');
      return;
    }
    fail(res, 500, 'internal_error', 'Unexpected error.');
  }
}
