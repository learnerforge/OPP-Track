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
