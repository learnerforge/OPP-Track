import { useEffect, useMemo, useState } from "react";
import Nav from "../components/Nav";
import { isLoggedIn } from "../auth";
import { navigate } from "../router";
import {
  EDITABLE_FIELDS,
  FIELD_LABELS,
  applyEdits,
  loadCatalog,
  loadEdits,
  parsePrize,
  recordId,
  saveEdit,
  type EditableField,
  type LoadedCatalog,
  type Opportunity,
  type StoredEdit,
} from "../data";
import {
  formatDistance,
  hydrateCoords,
  isNonPhysical,
  resolveCoord,
  haversineKm,
  type Coord,
} from "../location";

/** Sort keys offered in the toolbar. */
type SortKey =
  | "deadline-asc"
  | "deadline-desc"
  | "prize-desc"
  | "prize-asc"
  | "added-desc"
  | "title-asc"
  | "source-asc"
  | "location-near"
  | "location-asc";

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "deadline-asc", label: "Deadline · soonest" },
  { value: "deadline-desc", label: "Deadline · latest" },
  { value: "prize-desc", label: "Prize · highest" },
  { value: "prize-asc", label: "Prize · lowest" },
  { value: "location-near", label: "Location · nearest to me" },
  { value: "location-asc", label: "Location · A–Z" },
  { value: "added-desc", label: "Recently added" },
  { value: "title-asc", label: "Title · A–Z" },
  { value: "source-asc", label: "Source · A–Z" },
];

/**
 * Sort a copy of the visible items.
 *
 * Every key puts items with no value for that field last, whichever direction
 * is chosen — an empty deadline is not the "soonest" one, and an unpublished
 * prize is not the "lowest" one. Ties fall back to title so the order is
 * stable rather than dependent on the input sequence.
 *
 * `origin` is the viewer's coordinates, used only by `location-near`. When it
 * is null (geolocation unavailable or declined) the nearest-sort degrades to
 * "within India first, then A–Z", which is still a useful ordering rather than
 * a meaningless one.
 */
function sortItems(
  items: Opportunity[],
  key: SortKey,
  origin: Coord | null,
): Opportunity[] {
  const byTitle = (a: Opportunity, b: Opportunity) =>
    a.title.localeCompare(b.title, undefined, { sensitivity: "base" });

  const copy = [...items];
  copy.sort((a, b) => {
    switch (key) {
      case "deadline-asc":
      case "deadline-desc": {
        const av = a.deadline || "";
        const bv = b.deadline || "";
        if (!av && !bv) return byTitle(a, b);
        if (!av) return 1;
        if (!bv) return -1;
        const cmp = av.localeCompare(bv);
        return key === "deadline-asc" ? cmp || byTitle(a, b) : -cmp || byTitle(a, b);
      }
      case "prize-desc":
      case "prize-asc": {
        const ap = parsePrize(a.prize_pool);
        const bp = parsePrize(b.prize_pool);
        if (!ap && !bp) return byTitle(a, b);
        if (!ap) return 1;
        if (!bp) return -1;
        // Amounts are only comparable inside one currency.
        if (ap.currency !== bp.currency) return ap.currency.localeCompare(bp.currency);
        const cmp = ap.amount - bp.amount;
        return key === "prize-desc" ? -cmp || byTitle(a, b) : cmp || byTitle(a, b);
      }
      case "location-near": {
        const ac = resolveCoord(a.location);
        const bc = resolveCoord(b.location);
        // Unplaceable or online-located items sort last.
        if (!ac && !bc) return byTitle(a, b);
        if (!ac) return 1;
        if (!bc) return -1;
        if (origin) {
          const cmp = haversineKm(origin, ac) - haversineKm(origin, bc);
          return cmp || byTitle(a, b);
        }
        return byTitle(a, b);
      }
      case "location-asc": {
        const av = (a.location || "").trim();
        const bv = (b.location || "").trim();
        if (!av && !bv) return byTitle(a, b);
        if (!av) return 1;
        if (!bv) return -1;
        return (
          av.localeCompare(bv, undefined, { sensitivity: "base" }) || byTitle(a, b)
        );
      }
      case "added-desc": {
        const av = a.date_added || "";
        const bv = b.date_added || "";
        if (!av && !bv) return byTitle(a, b);
        if (!av) return 1;
        if (!bv) return -1;
        return -av.localeCompare(bv) || byTitle(a, b);
      }
      case "source-asc": {
        const cmp = a.source.localeCompare(b.source, undefined, {
          sensitivity: "base",
        });
        return cmp || byTitle(a, b);
      }
      case "title-asc":
      default:
        return byTitle(a, b);
    }
  });
  return copy;
}

/**
 * Inline edit form for one opportunity.
 *
 * Kept as a small controlled component so the parent list stays a simple map.
 * Saving goes through `saveEdit` → POST /api/edits (the shared store); the
 * parent merges the returned override so the row updates without a refetch.
 */
function EditRow({
  item,
  onSaved,
  onCancel,
}: {
  item: Opportunity;
  onSaved: (id: string, edit: StoredEdit) => void;
  onCancel: () => void;
}) {
  const id = recordId(item);
  const [draft, setDraft] = useState<Record<EditableField, string>>(() => {
    const initial = {} as Record<EditableField, string>;
    for (const field of EDITABLE_FIELDS) initial[field] = item[field] ?? "";
    return initial;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) {
      setError("This item has no stable id and cannot be edited.");
      return;
    }
    setSaving(true);
    setError(null);
    // Only send fields that actually changed.
    const changed: Partial<Record<EditableField, string>> = {};
    for (const field of EDITABLE_FIELDS) {
      if (draft[field] !== (item[field] ?? "")) changed[field] = draft[field];
    }
    if (Object.keys(changed).length === 0) {
      setSaving(false);
      onCancel();
      return;
    }
    const res = await saveEdit(id, changed);
    setSaving(false);
    if (!res.ok || !res.edit) {
      setError(res.error ?? "Save failed.");
      return;
    }
    onSaved(id, res.edit);
  };

  return (
    <form onSubmit={submit} className="mt-3 space-y-2 rounded-md border border-rule-strong bg-paper-raised p-3">
      <div className="grid gap-2 sm:grid-cols-2">
        {EDITABLE_FIELDS.map((field) => (
          <label key={field} className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-widest text-ink-muted">
              {FIELD_LABELS[field]}
            </span>
            <input
              value={draft[field]}
              onChange={(e) => setDraft((d) => ({ ...d, [field]: e.target.value }))}
              className="rounded-md border border-rule-strong bg-surface px-2 py-1.5 text-sm text-ink outline-none focus:border-accent"
            />
          </label>
        ))}
      </div>
      {error && <p className="text-sm text-critical">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-md border border-ink bg-ink px-3 py-1.5 text-sm text-paper disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-rule-strong px-3 py-1.5 text-sm text-ink-soft hover:bg-paper-raised"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

/** Gated events page — only rendered for a logged-in session. */
export default function Events() {
  const [data, setData] = useState<LoadedCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("All");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("deadline-asc");

  // Shared edits + whether the deployment can store them at all.
  const [edits, setEdits] = useState<Record<string, StoredEdit>>({});
  const [editsConfigured, setEditsConfigured] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Viewer coordinates for the nearest-location sort.
  const [origin, setOrigin] = useState<Coord | null>(null);
  const [geoState, setGeoState] = useState<"idle" | "asking" | "denied" | "ready">("idle");

  // Gate: bounce to login when there is no session flag.
  useEffect(() => {
    if (!isLoggedIn()) navigate("/login");
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadCatalog()
      .then((res) => !cancelled && setData(res))
      .catch((err) => !cancelled && setError(String(err?.message ?? err)));
    loadEdits()
      .then((state) => {
        if (cancelled) return;
        setEdits(state.edits);
        setEditsConfigured(state.configured);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // Ask for the viewer's position only when the nearest-sort is chosen, so the
  // permission prompt is tied to a clear user action.
  useEffect(() => {
    if (sortKey !== "location-near" || origin || geoState === "asking") return;
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setGeoState("denied");
      return;
    }
    setGeoState("asking");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setOrigin({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setGeoState("ready");
      },
      () => setGeoState("denied"),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 600_000 },
    );
  }, [sortKey, origin, geoState]);

  const types = useMemo(() => {
    if (!data) return [];
    const set = new Set<string>();
    for (const item of data.items) if (item.type) set.add(item.type);
    return ["All", ...Array.from(set).sort()];
  }, [data]);

  /** Catalog with stored edits merged in. */
  const merged = useMemo(
    () => (data ? applyEdits(data.items, edits) : []),
    [data, edits],
  );

  // Load the scrape-time geocoding results (public/data/locations.json). When
  // they arrive, `coordsVersion` changes and the list re-sorts with the real
  // coordinates instead of the gazetteer fallback.
  const [coordsVersion, setCoordsVersion] = useState(0);
  useEffect(() => {
    let cancelled = false;
    hydrateCoords().then((n) => {
      if (!cancelled && n > 0) setCoordsVersion(n);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = merged.filter((item) => {
      if (typeFilter !== "All" && item.type !== typeFilter) return false;
      if (!q) return true;
      return (
        item.title.toLowerCase().includes(q) ||
        item.source.toLowerCase().includes(q)
      );
    });
    return sortItems(filtered, sortKey, origin);
    // coordsVersion is deliberately a dependency: it is not read in the body,
    // but it signals that `resolveCoord` now returns better values.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [merged, typeFilter, query, sortKey, origin, coordsVersion]);

  const onSaved = (id: string, edit: StoredEdit) =>
    setEdits((prev) => ({ ...prev, [id]: edit }));

  if (!isLoggedIn()) {
    return (
      <>
        <Nav />
        <main className="mx-auto max-w-5xl px-6 py-20 text-ink-muted">
          Redirecting to login…
        </main>
      </>
    );
  }

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
              Members only
            </p>
            <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-ink">
              Events
            </h1>
          </div>
          {data && (
            <p className="text-sm text-ink-muted">
              {visible.length.toLocaleString()} of{" "}
              {merged.length.toLocaleString()} items
              {data.manifest && (
                <> · updated {data.manifest.generated_at.slice(0, 10)}</>
              )}
            </p>
          )}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search title or source…"
            className="w-64 rounded-md border border-rule-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent"
          />
          <label className="flex items-center gap-2 text-sm text-ink-muted">
            <span className="font-mono text-xs uppercase tracking-widest">
              Sort
            </span>
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="rounded-md border border-rule-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-wrap gap-2">
            {types.map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={
                  "rounded-full border px-3 py-1 text-sm " +
                  (t === typeFilter
                    ? "border-ink bg-ink text-paper"
                    : "border-rule-strong text-ink-soft hover:bg-paper-raised")
                }
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {sortKey === "location-near" && (
          <p className="mt-3 text-sm text-ink-muted">
            {geoState === "ready" && origin
              ? "Sorted by distance from your current location."
              : geoState === "denied"
                ? "Location unavailable — showing placeable locations first, then A–Z."
                : "Requesting your location…"}
          </p>
        )}

        {error && (
          <p className="mt-8 rounded-md bg-critical-soft px-4 py-3 text-sm text-critical">
            {error}
          </p>
        )}

        {!data && !error && (
          <p className="mt-10 text-ink-muted">Loading catalog…</p>
        )}

        {data && (
          <ul className="mt-8 divide-y divide-rule border-y border-rule">
            {visible.map((item) => {
              const id = recordId(item);
              const dist =
                sortKey === "location-near" && origin
                  ? (() => {
                      const c = resolveCoord(item.location);
                      return c ? haversineKm(origin, c) : null;
                    })()
                  : null;
              return (
                <li key={item.link || `${item.source}:${item.title}`} className="py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <a
                        href={item.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-ink hover:text-accent"
                      >
                        {item.title}
                      </a>
                      {item.edited && (
                        <span className="ml-2 rounded-full bg-safe-soft px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-safe">
                          edited
                        </span>
                      )}
                      <p className="mt-1 text-sm text-ink-muted">
                        {item.source}
                        {item.eligibility && <> · {item.eligibility}</>}
                        {item.location && (
                          <>
                            {" · "}
                            {item.location}
                            {isNonPhysical(item.location) ? null : dist !== null ? (
                              <span className="text-ink-soft"> ({formatDistance(dist)})</span>
                            ) : null}
                          </>
                        )}
                      </p>
                      {item.prize_pool && (
                        <p className="mt-1 font-mono text-xs text-safe">
                          {item.prize_pool}
                        </p>
                      )}
                    </div>
                    <div className="shrink-0 text-right">
                      <span className="rounded-md bg-paper-raised px-2 py-1 font-mono text-xs text-ink-soft">
                        {item.type}
                      </span>
                      {item.deadline && (
                        <p className="mt-1.5 font-mono text-xs text-ink-muted">
                          {item.deadline}
                        </p>
                      )}
                      <button
                        type="button"
                        onClick={() => setEditingId(editingId === id ? null : id)}
                        disabled={!id || !editsConfigured}
                        title={
                          !editsConfigured
                            ? "Editing is not configured on this deployment"
                            : !id
                              ? "This item has no stable id"
                              : "Edit this opportunity"
                        }
                        className="mt-2 block rounded-md border border-rule-strong px-2 py-1 font-mono text-xs text-ink-soft hover:bg-paper-raised disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {editingId === id ? "Close" : "Edit"}
                      </button>
                    </div>
                  </div>
                  {editingId === id && (
                    <EditRow
                      item={item}
                      onSaved={(savedId, edit) => {
                        onSaved(savedId, edit);
                        setEditingId(null);
                      }}
                      onCancel={() => setEditingId(null)}
                    />
                  )}
                </li>
              );
            })}
            {visible.length === 0 && (
              <li className="py-10 text-center text-ink-muted">
                No items match this filter.
              </li>
            )}
          </ul>
        )}
      </main>
    </>
  );
}
