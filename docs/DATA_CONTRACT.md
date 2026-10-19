# Data Contract — OPP-Track

> Distilled from `fullstack.md` §11.2 (the data contract), §11.3 (protection
> controls **#1, #3, #8, #9**), §14.2 (target layout) and §14.3 (ownership).
> Milestone **E1 — protect the data**. This file documents the contract;
> enforcement lives in the pipeline (`run_all.py` → validation →
> `sanity_gate.py` → `publish_dataset.py`).

## 1. The store — one JSON file, complete

`data/scraped_opportunities.json` is **the only data store**: a plain **array**
of opportunity objects — no wrapper object, so nothing about the current app
breaks. All metadata (counts, histograms, checksum, provenance) lives in
`data/manifest.json`, not in the data file. The canonical file is **tracked in
git** (control #1): until E1 it was gitignored and existed on exactly one
machine — that was the protection gap (B9/B26).

## 2. File inventory — one writer each (§14.3)

| Path | Role | Sole writer | Readers | Git |
|---|---|---|---|---|
| `data/scraped_opportunities.json` | **canonical dataset — the only data store** | `run_all.py` (pipeline) | `publish_dataset.py`, `regenerate_seeds.py`, `api/_lib/loadDataset.ts` | **tracked** |
| `data/manifest.json` | `schema_version`, counts, `type_histogram`, `per_source_counts`, `sha256`, `run_id`, `git_commit`, versions | `publish_dataset.py` | `verify.yml`, `/api/health`, the SPA | tracked |
| `data/reports/publish-YYYYMMDD.md` | publish report: validation result + new/removed/changed diff | `publish_dataset.py` | humans, `/api/report/latest` | tracked (append-only) |
| `data/scraper_health.json` | per-source health map (feeds `/api/sources`) — real filename is singular **`scraper_health`** | pipeline (`health_check.py` via `run_all.py`) | `/api/sources` | tracked |
| `public/data/manifest.json` | published pointer the app reads first (cache-busting) | `publish_dataset.py` | browser, monitors | generated at publish, ignored |
| `public/data/opportunities.<sha8>.json` | published copy, **byte-identical**, immutable filename | `publish_dataset.py` | browser, monitors | generated at publish, ignored |
| `data/backups/scraped_YYYYMMDD_HHMMSS.json` | rotation: newest per day × 7 + newest per ISO week × 8 | `scripts/rotate_backups.py` | restore drill | **ignored** |
| `src/lib/storage.ts` → `SEED_DATA` | bundled snapshot, first paint / offline fallback only | `scripts/regenerate_seeds.py` **only** | Vite build, `tests/migration.test.mjs` | tracked (`src/` frozen) |

**Rule: no file has two writers.** That is the point of the table — the class
of bug where a refresh overwrites a fix (B6/B7/B8) becomes structurally
impossible rather than merely unlikely.

## 3. Item shape

Required fields:

`id`, `title`, `type`, `source`, `link`, `deadline`, `eligibility`, `tags[]`,
`status`, `notes`, `date_added`

Optional fields:

`location`, `prize_pool`, `participants`, `organizer`, `duration`,
`quality_score`

## 4. Contracts (hard rules — both sides must honour them)

1. **Enum:** `type ∈ {Hackathon, Internship, Certification, Competition}`.
   Validation rejects anything else.
2. **`deadline: ''` means rolling/evergreen.** An empty deadline is a real,
   meaningful value (B2/F1) — **never fabricate a date** for an evergreen
   item. Dated deadlines are `YYYY-MM-DD`.
3. **`link` is a valid `http(s)` URL or empty, and is never fabricated** (B11).
   A missing link stays empty (with a `link_missing` marker) — synthesised
   `<base>/search?q=…` URLs are forbidden.
4. **Identity = stable fingerprint-hash ids** (B6/B24). The `id` is the join
   key between the published JSON and a visitor's local state; it must not
   churn across refreshes unless the item's content fingerprint changes.
5. **Integrity = `sha256` of the exact bytes**, computed **after** validation
   (never before), recorded in `data/manifest.json`, verified by
   `/api/health` and by the app when it fetches.
6. **Completeness:** every copy of the data is the **COMPLETE** set (2,588
   validated items as of 2026-10-19) — **never truncated, sampled or top-N**.
   Bundled snapshot, browser cache, published asset and exports are all the
   same complete set, so a visitor with no network still sees the whole
   catalog.

## 5. Protection controls in E1 scope (§11.3)

| # | Control | Where it lives |
|---|---|---|
| 1 | **Track the canonical JSON in git** | removed from `.gitignore`; acceptance: `git ls-files data/scraped_opportunities.json` is non-empty |
| 3 | **Atomic writes** in every writer: temp file → `fsync` → `os.replace` | all writers, including `scripts/rotate_backups.py` |
| 8 | **Backups + a tested restore drill** (revert commit → tag → artifact → Release) | `data/backups/` via `scripts/rotate_backups.py` |
| 9 | **Bounded repo growth** | `data/*` ignored except canonical/manifest/reports; `linguist-generated` via `.gitattributes`; monthly squash decision point |

### Backup rotation — exact CLI

```
python scripts/rotate_backups.py --file data/scraped_opportunities.json --dir data/backups --keep-daily 7 --keep-weekly 8 [--dry-run]
```

- Writes `data/backups/scraped_YYYYMMDD_HHMMSS.json` (UTC timestamp) atomically.
- Retention: the newest backup of each of the last **7 distinct calendar
  days** and the newest of each of the last **8 distinct ISO weeks**; the rest
  are deleted. Files whose names don't match the backup pattern are never
  touched.
- The canonical file is only ever **read** — rotation never modifies it.
- `--dry-run` prints the plan and changes nothing. Exit 0 on success, 1 on
  error. Stdlib only; safe to re-run (idempotent).

## 6. Filename gotcha

The health file is `data/scraper_health.json` — **singular** `scraper`.
There is no `scrapers_health.json`.
