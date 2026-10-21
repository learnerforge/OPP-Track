import { useEffect, useMemo, useState } from "react";
import Nav from "../components/Nav";
import { isLoggedIn } from "../auth";
import { navigate } from "../router";
import {
  loadCatalog,
  parsePrize,
  type LoadedCatalog,
  type Opportunity,
} from "../data";

/** Sort keys offered in the toolbar. */
type SortKey =
  | "deadline-asc"
  | "deadline-desc"
  | "prize-desc"
  | "prize-asc"
  | "added-desc"
  | "title-asc"
  | "source-asc";

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "deadline-asc", label: "Deadline · soonest" },
  { value: "deadline-desc", label: "Deadline · latest" },
  { value: "prize-desc", label: "Prize · highest" },
  { value: "prize-asc", label: "Prize · lowest" },
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
 */
function sortItems(items: Opportunity[], key: SortKey): Opportunity[] {
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

/** Gated events page — only rendered for a logged-in session. */
export default function Events() {
  const [data, setData] = useState<LoadedCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("All");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("deadline-asc");

  // Gate: bounce to login when there is no session flag.
  useEffect(() => {
    if (!isLoggedIn()) navigate("/login");
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadCatalog()
      .then((res) => !cancelled && setData(res))
      .catch((err) => !cancelled && setError(String(err?.message ?? err)));
    return () => {
      cancelled = true;
    };
  }, []);

  const types = useMemo(() => {
    if (!data) return [];
    const set = new Set<string>();
    for (const item of data.items) if (item.type) set.add(item.type);
    return ["All", ...Array.from(set).sort()];
  }, [data]);

  const visible = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    const filtered = data.items.filter((item) => {
      if (typeFilter !== "All" && item.type !== typeFilter) return false;
      if (!q) return true;
      return (
        item.title.toLowerCase().includes(q) ||
        item.source.toLowerCase().includes(q)
      );
    });
    return sortItems(filtered, sortKey);
  }, [data, typeFilter, query, sortKey]);

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
              {data.items.length.toLocaleString()} items
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
            {visible.map((item) => (
              <li
                key={item.link || `${item.source}:${item.title}`}
                className="py-4"
              >
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
                    <p className="mt-1 text-sm text-ink-muted">
                      {item.source}
                      {item.eligibility && <> · {item.eligibility}</>}
                      {item.location && <> · {item.location}</>}
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
                  </div>
                </div>
              </li>
            ))}
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
