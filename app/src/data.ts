/**
 * Catalog loader for the public app — manifest-first ladder (fullstack.md 11.5).
 *
 *   1. /data/manifest.json            (published counts + the immutable filename)
 *   2. /data/<published_file>         (the immutable, sha-named snapshot)
 *   3. /api/opportunities?page_size=  (function fallback, clamped server-side)
 *
 * The catalog is READ-ONLY here; nothing in this app writes to the dataset.
 */

export interface Opportunity {
  id?: string;
  title: string;
  type: string;
  source: string;
  link: string;
  deadline: string;
  eligibility?: string;
  tags?: string[];
  location?: string;
  prize_pool?: string;
  participants?: string;
  organizer?: string;
  duration?: string;
  date_added?: string;
  notes?: string;
  /** True when this record carries a stored user edit. */
  edited?: boolean;
  /** When the edit was saved (ISO). */
  edited_at?: string;
}

/** A stored user override for one opportunity, as returned by /api/edits. */
export interface StoredEdit {
  fields: Partial<Record<EditableField, string>>;
  updated_at: string;
  updated_by: string;
}

/** Fields a user may edit — mirrors api/_lib/edits.ts EDITABLE_FIELDS. */
export const EDITABLE_FIELDS = [
  "title",
  "type",
  "link",
  "deadline",
  "location",
  "prize_pool",
  "eligibility",
  "notes",
] as const;

export type EditableField = (typeof EDITABLE_FIELDS)[number];

/** Human labels for the edit form. */
export const FIELD_LABELS: Record<EditableField, string> = {
  title: "Title",
  type: "Type",
  link: "Link",
  deadline: "Deadline",
  location: "Location",
  prize_pool: "Prize",
  eligibility: "Eligibility",
  notes: "Notes",
};

/** Which field a prize string belongs to, so 1,000 USD never sorts above 2,000. */
export interface PrizeValue {
  amount: number;
  currency: string;
}

/**
 * Currency tokens, strongest signal first. Both a symbol/word before the amount
 * ("$29,376", "Rs. 50,000") and a code after it ("10,000 AUD", "1500万円") are
 * recognised. Currencies are not converted — comparing across them would be
 * inventing an exchange rate — so the amount is only meaningful within a
 * currency, which is how the sort uses it.
 */
const CURRENCY_PATTERNS: [RegExp, string][] = [
  [/(?:₹|\brs\.?\b|\binr\b)/i, "inr"],
  [/€|\beur\b/i, "eur"],
  [/\$|\busd\b/i, "usd"],
  [/£|\bgbp\b/i, "gbp"],
  [/\bchf\b/i, "chf"],
  [/\bzar\b|\br\d/i, "zar"],
  [/\baud\b/i, "aud"],
  [/\bcad\b/i, "cad"],
  [/\bsgd\b/i, "sgd"],
  [/\bjpy\b|万円|円|¥/i, "jpy"],
];

/** Locate the currency of a prize string, or null when none is stated. */
function findCurrency(text: string): { token: string; index: number } | null {
  let best: { token: string; index: number } | null = null;
  for (const [re, token] of CURRENCY_PATTERNS) {
    const m = text.match(re);
    if (m && m.index !== undefined) {
      if (!best || m.index < best.index) best = { token, index: m.index };
    }
  }
  return best;
}

/**
 * Read a number from a prize fragment, tolerating grouped digits.
 *
 * Handles both Western grouping ("1,000,000") and Indian lakh grouping
 * ("1,00,000"), plus space grouping ("250 000").
 */
function readAmount(fragment: string): number | null {
  const cleaned = fragment.replace(/(?<=\d)[,\s](?=\d)/g, "");
  const m = cleaned.match(/\d+(?:\.\d+)?/);
  if (!m) return null;
  const amount = Number(m[0]);
  return Number.isFinite(amount) && amount > 0 ? amount : null;
}

/**
 * Parse a free-text prize pool into a comparable amount.
 *
 * Handles "$29,376", "€12,000", "Rs. 50,000", "₹1,00,000", "10,000 AUD",
 * "1000 CHF" and "1500万円". Returns null when there is no number to read, so
 * non-cash prizes ("Goodies", "Certificate of Excellence") are excluded rather
 * than sorted as zero.
 */
export function parsePrize(raw?: string): PrizeValue | null {
  if (!raw) return null;
  const text = raw.trim();
  if (!text) return null;

  const cur = findCurrency(text);
  if (!cur) return null;

  // The number may sit on either side of the currency token: "$29,376" and
  // "1500万円" put it after/before respectively. Try the tail first (the common
  // case, and the only correct one for "R250 000" where the R prefix is part of
  // the symbol), then fall back to the head.
  const after = readAmount(text.slice(cur.index));
  const amountFromText = after ?? readAmount(text.slice(0, cur.index));
  if (amountFromText === null) return null;

  // 万 is a ten-thousand multiplier, so "1500万円" is ¥15,000,000 — without
  // this, Japanese prizes sort ~10,000x too low.
  const amount =
    cur.token === "jpy" && text.includes("万")
      ? amountFromText * 10000
      : amountFromText;

  return { amount, currency: cur.token };
}

export interface Manifest {
  item_count: number;
  type_histogram: Record<string, number>;
  per_source_counts: Record<string, number>;
  sha256: string;
  published_sha8: string;
  published_file: string;
  generated_at: string;
}

export interface LoadedCatalog {
  items: Opportunity[];
  manifest: Manifest | null;
  /** Which rung of the ladder served the data. */
  origin: "manifest-asset" | "api-fallback";
}

function pickItems(payload: unknown): Opportunity[] | null {
  if (Array.isArray(payload)) return payload as Opportunity[];
  if (payload && typeof payload === "object") {
    const rec = payload as Record<string, unknown>;
    for (const value of Object.values(rec)) {
      if (Array.isArray(value)) return value as Opportunity[];
    }
    if (Array.isArray(rec.items)) return rec.items as Opportunity[];
  }
  return null;
}

/** Load the manifest, tolerating a missing/corrupt file. */
export async function loadManifest(): Promise<Manifest | null> {
  try {
    const res = await fetch("/data/manifest.json", { cache: "no-cache" });
    if (!res.ok) return null;
    return (await res.json()) as Manifest;
  } catch {
    return null;
  }
}

/** Load the full catalog via the ladder. Throws only if every rung fails. */
export async function loadCatalog(): Promise<LoadedCatalog> {
  const manifest = await loadManifest();

  if (manifest?.published_file) {
    try {
      const res = await fetch(`/data/${manifest.published_file}`, {
        cache: "no-cache",
      });
      if (res.ok) {
        const items = pickItems(await res.json());
        if (items) return { items, manifest, origin: "manifest-asset" };
      }
    } catch {
      /* fall through to the API rung */
    }
  }

  // API fallback — server clamps page_size, so request a large page and accept
  // whatever the validator allows.
  const firstRes = await fetch("/api/opportunities?page_size=100&page=1", { cache: "no-cache" });
  if (!firstRes.ok) throw new Error(`catalog unavailable (HTTP ${firstRes.status})`);
  const firstBody = (await firstRes.json()) as { items?: unknown; total_pages?: unknown };
  const firstItems = pickItems(firstBody);
  if (!firstItems) throw new Error("catalog unavailable (unexpected shape)");
  const totalPages = typeof firstBody.total_pages === "number" ? firstBody.total_pages : 1;
  if (!Number.isInteger(totalPages) || totalPages < 1 || totalPages > 10_000) {
    throw new Error("catalog unavailable (invalid pagination metadata)");
  }
  if (totalPages === 1) return { items: firstItems, manifest, origin: "api-fallback" };

  const rest = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, i) => i + 2).map(async (page) => {
      const res = await fetch(`/api/opportunities?page_size=100&page=${page}`, { cache: "no-cache" });
      if (!res.ok) throw new Error(`catalog unavailable (HTTP ${res.status} on page ${page})`);
      const body = (await res.json()) as { items?: unknown };
      const items = pickItems(body);
      if (!items) throw new Error(`catalog unavailable (unexpected page ${page} shape)`);
      return items;
    }),
  );
  return { items: [firstItems, ...rest].flat(), manifest, origin: "api-fallback" };
}

/** Identity of an opportunity, matching the API's id/fingerprint rule. */
export function recordId(item: Opportunity): string {
  return item.id ?? "";
}

/**
 * Apply stored user edits over a catalog.
 *
 * The published snapshot is immutable and the pipeline rewrites it every 8
 * hours, so edits are layered on in the browser rather than written into it.
 * Records with no edit are returned by reference so React sees a stable list.
 */
export function applyEdits(
  items: Opportunity[],
  edits: Record<string, StoredEdit>,
): Opportunity[] {
  if (!edits || Object.keys(edits).length === 0) return items;
  return items.map((item) => {
    const id = recordId(item);
    const edit = id ? edits[id] : undefined;
    if (!edit?.fields) return item;
    const merged: Opportunity = { ...item };
    for (const field of EDITABLE_FIELDS) {
      const value = edit.fields[field];
      if (typeof value === "string") merged[field] = value;
    }
    merged.edited = true;
    merged.edited_at = edit.updated_at;
    return merged;
  });
}

/** Result of loading the shared edit store. */
export interface EditsState {
  edits: Record<string, StoredEdit>;
  /** False when the deployment has no Blob credentials — editing is disabled. */
  configured: boolean;
}

/**
 * Load the shared edit document. A failure degrades to "no edits, not
 * configured" so a storage outage never blocks reading the catalog.
 */
export async function loadEdits(): Promise<EditsState> {
  try {
    const res = await fetch("/api/edits", { cache: "no-cache" });
    if (!res.ok) return { edits: {}, configured: false };
    const body = (await res.json()) as Partial<EditsState>;
    return {
      edits: body.edits && typeof body.edits === "object" ? body.edits : {},
      configured: body.configured === true,
    };
  } catch {
    return { edits: {}, configured: false };
  }
}

/** Outcome of a save attempt, so the UI can show a real message. */
export interface SaveResult {
  ok: boolean;
  error?: string;
  edit?: StoredEdit;
}

/**
 * Save an edit through to the shared store.
 *
 * Goes to `/api/edits` (the only write path in the API). The `x-edits-token`
 * header carries the same shared secret the login gate uses, configured in the
 * app as VITE_EDITS_TOKEN at build time. When it is not configured the caller
 * gets a clear error rather than a silent no-op.
 */
export async function saveEdit(
  id: string,
  fields: Partial<Record<EditableField, string>>,
  updatedBy = "learnerforge",
): Promise<SaveResult> {
  const token = import.meta.env.VITE_EDITS_TOKEN as string | undefined;
  try {
    const res = await fetch("/api/edits", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "x-edits-token": token } : {}),
      },
      body: JSON.stringify({ id, fields, updated_by: updatedBy }),
    });
    const body = (await res.json().catch(() => ({}))) as {
      error?: string;
      edit?: StoredEdit;
    };
    if (!res.ok) return { ok: false, error: body.error ?? `save failed (HTTP ${res.status})` };
    return { ok: true, edit: body.edit };
  } catch (err) {
    return { ok: false, error: String((err as Error)?.message ?? err) };
  }
}
