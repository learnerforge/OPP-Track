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
}

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
  const res = await fetch("/api/opportunities?page_size=100", { cache: "no-cache" });
  if (!res.ok) throw new Error(`catalog unavailable (HTTP ${res.status})`);
  const items = pickItems(await res.json());
  if (!items) throw new Error("catalog unavailable (unexpected shape)");
  return { items, manifest, origin: "api-fallback" };
}
