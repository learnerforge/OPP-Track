# OPP-Track — Backend Audit, Scheduling & Vercel Deployment Plan

> **Scope** — backend only for the audit: scraper pipeline, data layer (`storage.ts` migration logic), validation tooling, build/dependency/CI configuration. The **frontend was audited on request in §12** (same working rule: no source file changed). It otherwise reappears only where a feature milestone in §11 requires it.
> **Added goal (2026‑10‑19, revised same day)** — deploy this as a **public catalog website whose backend is the pipeline itself**: a **scheduled engine** keeps the dataset fresh and Vercel serves it. **The database plan is withdrawn** — no Supabase, no PostgreSQL, no accounts, no auth. **The only data store is `.json`** (`data/scraped_opportunities.json` + a companion manifest), and that file is the single source of truth for **showing the complete dataset** on the site — every item, nothing truncated. Build plan: **§11** (file‑based data engine, milestones E1–E8) + **§14** (complete code‑base model, `src/` frozen); the four blocking decisions — all **settled 2026‑10‑19** — are recorded in **§14.8**.
> **Method** — full source audit plus live execution of the pipeline's own checks (2026‑10‑19): Python schema validation, `npm run validate`, `npm run typecheck`, `npm test`, `npm run build`, `npm ls`, `git ls-files`, dependency/lockfile inspection.
> **Tree state at audit time** — clean at commit `f489049`, **plus an uncommitted Tailwind v4 / shadcn‑ui migration in the working tree** (`package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig.json`, `src/components/ui/`, `shadcn-ui-ref/`). That migration is treated as user work and is only referenced here where it affects backend/deploy concerns.

---

## 0. Status addendum — 2026‑10‑21 (authoritative over the body where they disagree)

The plan body above describes the *original* design (a deploy of the existing `src/` app, no login). Execution diverged in four ways. Where §11/§14 contradict this section, **this section wins** until it is folded back in.

**1. The live site is a separate app in `app/`, not a deploy of `src/`.** The `src/` freeze (§14.1) made the existing app undeployable as‑is, so the public site was built self‑contained in `app/` (Vite + React, its own `index.css` theme subset, plain client router — no React Router dependency). Deploy was switched via `vercel.json` (`buildCommand: npm run build:app`, `outputDirectory: app/dist`). `src/` remains strictly frozen; nothing under it was created, edited, moved or deleted. Exception A (`regenerate_seeds.py` → `src/lib/storage.ts`) is still the only generator write; Exception B (the E6 allowlist entry) is still commented out in `docs/FREEZE_ALLOWLIST.md`.

**2. There *is* a login, and it is a UI‑only gate.** The body states "no accounts, no auth". Reality: a single hardcoded user (`learnerforge`) gates the `/events` page. It is deliberately a **client‑side gate** — the underlying `/api/*` and `/data/*.json` remain publicly readable, so the gate is presentational and **must not be described as security**. The password is stored as a SHA‑256 digest (`app/src/auth.ts`) so plaintext never ships. This is a product decision, not an oversight; a real auth layer would require a backend and is out of scope.

**3. Three pages ship, not the §11.4 surface.** `/` (public landing), `/login` (public), `/events` (gated). The 9 read‑only API functions and the manifest‑first data ladder (§11.5) exist and are used by the app; the app reads `/data/manifest.json` → the sha‑named snapshot → `/api/opportunities` as fallback.

**4. The catalog has one more source: `events.heapheaphurray.com`.** Added as `scripts/scrapers/heapheaphurray.py` and registered in `run_all.py`'s `SCRAPERS` map (so it runs on every pass, no `--multi` needed; it is deliberately *not* added to `sources.json`, which would be dead config since `SCRAPERS` takes precedence). It is an **aggregator**: every listing links out to the organiser's own page. Because Unstop, MLH, Devfolio, Devpost and HackIndia already scrape many of those pages first‑hand, the scraper carries a **cross‑source replica guard** that reads the current dataset and skips items whose normalised link *or* title already exists from another source. This keeps the "no replica of an opportunity from this website to another" requirement local to this source instead of hardcoding a host list that would rot.

**5. Shared dedup got stricter, deliberately.** `base.normalize_link()` now strips scheme, `www.`, *tracking‑only* query params (`utm_*`, `ref*`, `fbclid`, …) and the trailing slash before `deduplicate_by_link` compares. It does **not** strip meaningful query params or fragments: `?competition=<id>` distinguishes 44 SIGNATE competitions that share one path, and `#anchor` distinguishes NASA/Mitacs items that share one page. An earlier, blunter version was caught by regression test destroying 62 legitimate items — the narrow rule removes exactly 1 real duplicate from the 2,588.

**6. The sanity gate is size‑aware.** `scripts/sanity_gate.py` now skips the per‑source ±50% rule when the baseline is below `MIN_SOURCE_BASELINE` (5) and emits a warning instead. A 2‑item source dropping to 0 is "−100%" but says nothing about scrape health; four consecutive scheduled runs were blocked by exactly that false positive while the run itself was healthy (2,577 vs 2,588 items, −0.4%, well inside ±20%).

**7. `run_all.py` refuses to clobber the canonical dataset.** A single‑source run (`--source X`, or any of the legacy per‑site flags) that would write to `data/scraped_opportunities.json` now exits 2 and prints the fix. The dataset was silently overwritten three times by exactly that command.

**8. Frontend sorting.** `/events` supports sorting by deadline (soonest/latest), prize (highest/lowest), recently added, title and source, plus the existing type filter and search. `app/src/data.ts` exports `parsePrize()`, which normalises free‑text prize strings (`$29,376`, `€12,000`, `₹1,00,000`, `10,000 AUD`, `R250 000 ZAR`, `1500万円` → ×10,000) and returns `null` for non‑cash prizes so they sort last rather than as zero. Currencies are compared within a currency only — no invented exchange rates.

**9. Opportunities are editable, and edits persist to a real store.** Each row on `/events` has an **Edit** button that opens an inline form for `title`, `type`, `link`, `deadline`, `location`, `prize_pool`, `eligibility` and `notes`. Saving goes through the **only write path in the API**, `POST /api/edits`, which stores the override as a JSON document in **Vercel Blob** (`edits/catalog-edits.json`) — the option chosen over re‑introducing Postgres or a KV store. The scraped dataset is *never* modified: a published scrape overwrites `data/scraped_opportunities.json` every 8 hours, so edits live beside it and are merged over the catalog at read time (in `/api/opportunities`, `/api/opportunities/[id]` and in the app via `applyEdits`). This is what makes an edit survive the next publish. The route **fails closed**: with no `BLOB_READ_WRITE_TOKEN` it returns `503 edits_not_configured` rather than a fake success, and with no `EDITS_TOKEN` the write path is closed rather than left world‑writable. Credentials are Vercel env vars only, never committed. **Requires two env vars:** `BLOB_READ_WRITE_TOKEN` (from a Vercel Blob store) and `EDITS_TOKEN` (any shared secret), plus `VITE_EDITS_TOKEN` set to the same `EDITS_TOKEN` value so the browser can authenticate the write. Until they are set, the Edit button is disabled with an explanatory tooltip. Each record also accepts only the allow‑listed fields, so a hand‑crafted body cannot inject arbitrary keys.

**10. Location sort uses proximity to the viewer.** Two new sort keys: **Location · nearest to me** and **Location · A–Z**. The nearest sort asks for the browser's geolocation (only when that option is selected, so the permission prompt follows a clear user action) and ranks items by great‑circle distance. Distance is shown per row (`12 km`, `1,240 km`). Because the scraped `location` field is free text, `app/src/location.ts` carries a bounded **gazetteer** (≈270 cities, 65 country centroids) plus alias handling for the several shapes actually observed — `"Bengaluru, India"`, `"Cincinnati, OH"`, `"US, WA, Seattle"`, `"MX, DIF, Mexico City"` — and deliberately places **online/remote and junk values** (`Online`, `Remote`, `Various`, `Offline`, `Prize`, `REGISTERING`) with no coordinates so they always sort last instead of claiming a false "nearest" position. No geocoding API is called at request time: it would add a network dependency and a key to every page load. Two‑letter codes are resolved by **position, not value**, because `CA`/`DE`/`ID`/`IL`/`IN`/`CO` are simultaneously country and US‑state codes — `"Calgary, CA"` resolves to Canada while `"Cincinnati, OH"` resolves to the USA. If the user declines geolocation the sort degrades to "placeable locations first, then A–Z" rather than becoming meaningless.

**Still open (unchanged by the above):** fresh publishing is blocked by the gate on genuinely‑decaying sources, not by the false‑positive class (see §11.8); Vercel's GitHub App is not yet installed on `learnerforge/OPP-Track`, so data commits do not auto‑deploy; Topcoder and HackerEarth are both now **anti‑bot blocked on the headless path** while still answering plain HTTP — Topcoder's public challenge API has been retired (all `v4`/`v5` endpoints 404), and HackerEarth's reachable JSON endpoint (`/api/community/challenges/compete/`) returns a stale historical set, not a live listing. The edit store (§0.9) additionally needs `BLOB_READ_WRITE_TOKEN`, `EDITS_TOKEN` and `VITE_EDITS_TOKEN` set in Vercel before editing is enabled.

---

## 1. Executive Summary

The repository has silently outgrown its own documentation: `docs/ARCHITECTURE.md` still describes a manual, human‑paste tracker with "no scraper to maintain", while the codebase is actually an **89‑site scraping pipeline → seed generator → static React app** with a versioned localStorage migration layer. The backend works, but it is entirely manual and machine‑dependent.

| Check | Result |
|---|---|
| `npm run typecheck` | ✅ pass |
| `npm test` | ✅ 23/23 |
| `npm run build` | ✅ (JS 1.56 MB / 226 KB gzip) |
| Python `run_all.py --validate` | ✅ 2,577 items, 0 errors |
| `npm run validate` | ❌ **3,968 errors, 637 warnings** |
| `npm run lint` | ❌ eslint not installed |
| CI / scheduler | ❌ none exists |
| Python dependency manifest | ❌ none exists |
| Secrets committed | ✅ none found (grep‑verified) |
| Frontend audit (§12) | ⚠️ 21 findings, 4 High — 1,718 items show "NaN days left", a reminder‑storm bug, seed‑id migration drift, and a plan‑vs‑tree mismatch |

**Five findings block a reliable scheduled + Vercel deployment today** (B1–B5). The recommended target architecture: **GitHub Actions runs the heavy browser‑based scraping; Vercel hosts the static app and serves refreshed data as a CDN‑cached JSON artifact; the app fetches data at runtime instead of bundling 2,577 records into the JS bundle.**

---

## 2. As‑Built Architecture (data flow)

```
84 built-in scrapers (scripts/scrapers/*.py)   ┐
+ sources.json registry (60 entries, 5 unique) ┘
        │  run_all.py [--multi] [--detailed]
        ▼
  fingerprint dedup → link dedup → stale/expired filter → quality scoring
        │  (--detailed: detail-page enrichment, 5 platforms only)
        ▼
  data/scraped_opportunities.json   (gitignored, ~2,577 items)
        │  scripts/regenerate_seeds.py
        ▼
  src/lib/storage.ts  SEED_DATA     (committed, 1.6 MB / ~39.6k lines, SEED_VERSION 9)
        │  Vite build (tsc && vite build)
        ▼
  dist/ → static hosting
        │  first visit: SEED_DATA written to localStorage
        ▼
  localStorage: user state (status/notes) + version-keyed migration on refresh
```

**Documented vs. real:** `docs/ARCHITECTURE.md` §1–2 (manual tracker, "no scraper to maintain") no longer matches reality — a documentation finding in its own right (B22).

---

## 3. What Is Healthy (keep it)

- **`base.py` utility layer** — pure functions: multi‑format `parse_deadline`, `filter_stale` (expired + pre‑2024 year heuristics), two‑stage dedup (fingerprint + link, keeping the richer record), `classify_location`, `quality_score` (0–100 completeness). Clean and testable.
- **Security posture** — no API keys/secrets anywhere in scraper code (grep‑verified); `.gitignore` has a thorough secrets section (`.env*`, `*.key`, `credentials*`, etc.).
- **Migration layer** — `loadOpportunities()` preserves user edits (status/notes) across seed refreshes, drops removed seeds, appends additions; covered by 23 passing tests that import the real bundled module via esbuild.
- **Validator that works** — the Python‑side `run_all.py --validate` correctly validates all 2,577 current items.
- **Repo hygiene baseline** — `dist/`, `data/scraped_opportunities.json`, `data/new_seed_entries.*`, `__pycache__/`, logs are all ignored; typecheck and production build green.

---

## 4. Findings (prioritized)

| ID | Sev | Area | Finding |
|----|-----|------|---------|
| B1 | P0 | Deploy | Deploy‑critical state is uncommitted; Vercel builds from git |
| B2 | P0 | Validation | `npm run validate` red: 3,968 errors from 3 stale validator rules |
| B3 | P0 | Scheduling | No CI workflow / cron anywhere; refresh is manual only |
| B4 | P0 | Reproducibility | No Python dependency manifest (`requirements.txt`/`pyproject.toml`) |
| B5 | P0 | Tooling | `npm run lint` broken — eslint not installed |
| B6 | P1 | Data integrity | Positional seed IDs renumber each refresh → user status can attach to the wrong opportunity |
| B7 | P1 | Data integrity | `date_added` resets to scrape day for every item on every run |
| B8 | P1 | Tooling | `merge_seeds.py --auto` emits the pre‑v4 entry format → reintroduces TS2590 |
| B9 | P1 | Repo hygiene | 1.6 MB generated file + tracked generated artifacts (incl. two 1.8 MB backups) |
| B10 | P1 | Portability | Hardcoded Windows absolute paths; hardcoded stale date `2026-09-12` in 3 scripts; dead loop bug in `validate_live.py` |
| B11 | P1 | Data quality | `multi_source.py` fabricates `search?q=` URLs when no link is found |
| B12 | P1 | Data quality | Scholarships/fellowships are mis‑typed as Hackathon/Internship (9 sites) |
| B13 | P1 | Data quality | Per‑source duplicate‑title drop loses distinct same‑named events |
| B14 | P1 | Runtime | ~2 MB localStorage payload approaches Safari's quota; sync stringify on load |
| B15 | P2 | Runtime | Serial scraping (~60–90 min), no checkpointing — one crash loses the whole run |
| B16 | P2 | Runtime | No retry/backoff; bot‑blocked sources counted as successes |
| B17 | P2 | Runtime | `--detailed` enrichment covers only 5 platforms; no enrichment cache |
| B18 | P2 | Observability | Free‑text logs only; no run summary, no regression gate, no alerts |
| B19 | P2 | Repo hygiene | Dev/test scripts mixed into `scripts/scrapers/`; no Python tests |
| B20 | P2 | Config | `sources.json` metadata drift (`total_sources: 58` vs actual 60; 55 duplicated entries) |
| B21 | P2 | Docs | `ARCHITECTURE.md` / `SCRAPING_WORKFLOW.md` describe a system that no longer exists |
| B22 | P2 | Config | No Node version pin (`engines`/`.nvmrc`) |
| B23 | P2 | Config | Stale `postcss.config.js` (v3‑style plugins; `autoprefixer` removed from deps) |
| B24 | P2 | Data model | Fingerprint (title+source+type) breaks on retitling — unstable identity |
| B25 | P2 | Config | `allowScripts` field in `package.json` is not an npm feature (ignored) |
| B26 | P0 | Platform | The dataset is **untracked and unprotected** (`data/scraped_opportunities.json` is gitignored, exists only on one machine) and there is **no deployed, scheduled engine** — the deployed site can only go stale (plan: §11) |

### P0 — Deployment blockers

**B1 · Deploy‑critical state is uncommitted.**
Vercel (and any CI) builds from **git**, not the working tree. The working tree currently holds the Tailwind v4 / shadcn‑ui migration — dependency changes (`package.json`, `package-lock.json`), build config (`vite.config.ts`, `tsconfig.json`) and new source files (`src/components/ui/`, `src/lib/meta.ts`, `src/lib/utils.ts`, `src/components/Hero.tsx`). Deploying today would ship the old committed state.
*Recommendation:* commit before deploying; split into two commits (deps + build config, then UI) so a rollback can target one concern. Verify `typecheck`, `test`, `build`, `validate` all pass on the committed tree first.

**B2 · `npm run validate` is red — 3,968 errors / 637 warnings.**
The committed validator (`scripts/validate-data.mjs`) no longer matches the data model. Three root causes:

1. **ID regex too narrow** — `^seed_\d{3}$` rejects every id ≥ `seed_1000`; the regenerated dataset runs to `seed_2577` (≈1,577 false errors).
2. **Empty deadline treated as an error** — 1,718 evergreen items (courses, rolling job listings) legitimately have no deadline; the validator demands a valid `YYYY-MM-DD` for all.
3. **`Competition` missing from valid types** — 670 items flagged `invalid type 'Competition'`, although the `Opportunity` TypeScript union includes it.

*Impact:* any CI quality gate or pre‑deploy check fails; the script's exit code cannot be trusted, which also invalidates the 637 warnings (mostly genuine "deadline passed but still Not Started" signals).
*Recommendation:* fix the three rules (id pattern `seed_` + 4+ digits; deadline optional; add `Competition`); downgrade duplicate‑title to a warning when links differ (see B13). Acceptance: `npm run validate` exits 0 on current `SEED_DATA` **and still fails** on a deliberately corrupted fixture.

**B3 · No scheduled execution path.**
No `.github/workflows`, no `vercel.json`, no cron of any kind. Data refresh today is a multi‑command manual run on one Windows machine. This is the core issue addressed in §6.

**B4 · No Python environment manifest.**
No `requirements.txt` / `pyproject.toml`; `scrapling`, `httpx` and the patchright/playwright browser toolchain are unpinned, and the required browser install step (`patchright install chromium` plus OS libraries on Linux) is documented nowhere outside a one‑line mention in `SCRAPING_WORKFLOW.md`. A scheduled runner cannot reproduce the local environment; scraper libraries churn quickly, so drift will break runs silently.
*Recommendation:* a pinned `requirements.txt` (direct deps only, with hashes optional) + a documented browser‑install step for Linux CI.

**B5 · Broken lint gate.**
`npm run lint` invokes eslint, which is not installed (`npm ls eslint` → empty) and has no config file. The script has never been runnable.
*Recommendation:* either install + configure eslint (flat config) and wire it into CI, or delete the script so the toolchain reflects reality. Decision needed (§13).

### P1 — Correctness & data integrity

**B6 · Positional seed IDs (most severe user‑facing issue).**
`regenerate_seeds.py` numbers entries by array position (`seed_001…seed_2577`), and `storage.ts`'s migration reconciles localStorage against those ids: a stored seed whose id still exists and whose status is `Not Started` is replaced by the current canonical seed **with that id**. After any refresh, array positions shift, so an id can point to a *different* opportunity — a user's `Applied` status can silently attach to the wrong listing, and `Not Started` records get silently swapped.
*Recommendation:* derive stable ids from the fingerprint that `base.py` already computes (e.g. `seed_` + hash), and change migration matching to fingerprint/title+source. One‑time id‑mapping migration for existing localStorage users. Acceptance: after a refresh, every user status still sits on the same title+source.

**B7 · `date_added` resets every run.**
`ScrapeItem.date_added` defaults to scrape day, and every run rebuilds all items — so "added recently" filters and the Weekly Review view degrade after every refresh; the field loses its only meaning.
*Recommendation:* persist first‑seen dates keyed by fingerprint from the previous snapshot; only new items get today's date.

**B8 · Stale merge path reintroduces TS2590.**
`merge_seeds.py --auto` appends entries in the pre‑v4 format (no per‑entry `as Opportunity` assertion). Using it would regenerate the "union type too complex" compile error that forced the current per‑entry workaround.
*Recommendation:* retire `merge_seeds.py` in favour of `regenerate_seeds.py` (single supported path), or update it to the current format. Whichever is kept must be documented as *the* path (B21).

**B9 · Generated data lives in git.**
`src/lib/storage.ts` is now 1.6 MB / ~39,600 lines of generated content — every refresh is an unreviewable 38k‑line diff and permanent history bloat. Additionally, generated artifacts are tracked: `data/scraper_health.json`, `data/pipeline_results.json`, and two `data/scraped_opportunities_backup_*.json` (~1.8 MB each) — the `.gitignore` covers the main scrape file but not these variants.
*Recommendation:* broaden `.gitignore` to `data/*` with explicit exceptions; untrack the artifacts; longer term, move seed data out of source entirely (§8), which also deletes the TS2590 workaround.

**B10 · Hardcoded environment assumptions.**
- `health_check.py` inserts the literal Windows path `E:\GitHub Projects\OPP-Track` into `sys.path` and writes to an absolute Windows path — fails on any CI/Linux runner.
- `check_all_links.py`, `validate_live.py`, `validation_report.py` hardcode `today = date(2026, 9, 12)` — all freshness math has been silently wrong since 2026‑09‑13.
- `validate_live.py` contains a dead loop (`if sum(1 for _ in range(1)) >= 20: pass`) that prints **every** expired item before printing the sample again — noisy, misleading output.
*Recommendation:* derive repo root from `__file__` (as `run_all.py`/`enrich.py` already do), use `date.today()`, delete the dead loop.

**B11 · Fabricated links.**
`multi_source.py` synthesises a `<base>/search?q=<title>` URL when a card has no link selector match. These URLs usually 404 and pollute both the dataset and link audits.
*Recommendation:* drop the item or keep it with an empty link and a `link_missing` marker; never invent URLs.

**B12 · Type‑fidelity loss.**
`multi_source.py`'s `_TYPE_MAP` maps `scholarship → Hackathon` and `fellowship → Internship`. Nine sites (Buddy4Study, Fastweb, ScholarshipOwl, GSoC, Outreachy, MLH Fellowship, NSF REU, Mitacs, DAAD RISE) are therefore mis‑typed in the data, and the type is user‑visible.
*Recommendation:* adding `Scholarship`/`Fellowship` to the `Opportunity` union is the clean fix but touches the frontend (out of scope here); the backend can stage correct type strings first. Decision needed (§13).

**B13 · Duplicate‑title drop.**
Per‑source `seen_titles` skips any repeated title, so two distinct events sharing a name (e.g. weekly contest series, same hackathon name across chapters) are silently lost.
*Recommendation:* dedup by link/fingerprint; treat identical title **and** link as duplicate, title alone as insufficient.

**B14 · localStorage ceiling.**
2,577 seeds serialise to roughly 2 MB; combined with user data and version keys this approaches Safari's ~5 MB quota. `loadOpportunities` throws `StorageError` on quota failure (first paint becomes an error state), and the initial `JSON.stringify` of the whole list is a synchronous main‑thread cost on every cold load.
*Recommendation:* seeds fetched at runtime into memory (§8); localStorage keeps only user state (id → status/notes), which is kilobytes.

### P2 — Operations & maintainability

**B15 · Serial scraping, no checkpointing.** `run_all.py` runs sources one at a time (≈60–90 min for `--multi --detailed`) and writes the output file only at the very end — any mid‑run failure loses everything. `health_check.py` already demonstrates 8‑way threading safely.
*Recommendation:* per‑source checkpoint files, resume support, bounded parallelism with per‑domain throttling, and a configurable overall timeout.

**B16 · No retry/backoff; blocked ≠ failed.** One attempt per source; 403/429/5xx are indistinguishable from dead pages. Known bot‑blocked sources still run every time and count as successes (Himalayas 0/30 live, Remotive 0/16, LeetCode 12/103, LinkedIn 16/55 per the last audit).
*Recommendation:* retry with exponential backoff, per‑source health history, a distinct `blocked` status, and an allow‑list of skip‑if‑persistently‑blocked sources.

**B17 · Enrichment coverage & cache.** `enrich.py` recognises only Devfolio/Devpost/HackerEarth/Internshala/Unstop by hostname — `--detailed` does nothing for the other ~80 sources — and it refetches identical detail pages every run at a serial 2 s delay.
*Recommendation:* drive source detection from `sources.json` domains; add an on‑disk enrichment cache keyed by fingerprint + content hash with a TTL; parallelise with a small pool.

**B18 · No observability or regression gate.** Logs are free text. Nothing catches silent selector rot.
*Recommendation:* emit a machine‑readable run summary (per‑source counts, totals, blocked/error counts, timings, delta vs previous run) as a build artifact; fail the run when totals drop below ~60 % of the rolling baseline or when >40 % of sources error; surface it in the CI job summary and notify on failure.

**B19 · Dev scripts mixed with production scrapers; no Python tests.** `test_apis.py`, `test_devpost.py`, `test_hackerearth.py`, `test_mlh.py`, `test_unstop.py`, `test_investigate.py`, `_check.py`, `_run_new.py` sit inside `scripts/scrapers/`.
*Recommendation:* move to `scripts/debug/` (or delete); add pytest coverage for `base.py` (deadline formats, stale heuristics, fingerprint stability, dedup precedence) — these functions carry all the data‑quality logic and are currently untested.

**B20 · Registry drift.** `sources.json` declares `total_sources: 58` while holding 60 entries, and 55 of them duplicate built‑in scrapers (`run_all.py` skips overlaps, so behaviour is correct, but the registry misleads maintainers).
*Recommendation:* generate the registry view from code, or mark duplicates explicitly; validate the metadata field.

**B21 · Docs drift.** `ARCHITECTURE.md` describes a no‑scraper manual tracker; `SCRAPING_WORKFLOW.md` predates `--multi`, `--detailed` and `regenerate_seeds.py`.
*Recommendation:* rewrite both against the as‑built pipeline (§2), including the single supported refresh path.

**B22 · Node version not pinned.** No `engines` in `package.json`, no `.nvmrc`; Vercel's Node version floats between majors.
*Recommendation:* pin explicitly (local environment is Node 22).

**B23 · Stale `postcss.config.js`.** Still configures the v3‑style `tailwindcss` + `autoprefixer` plugins, but `autoprefixer` was removed from dependencies and is absent from `node_modules` (postcss remains only as a transitive Vite dependency). The current build happens to succeed, but the file is a landmine for the next Vite/PostCSS upgrade; with `@tailwindcss/vite` owning Tailwind v4, it should be removed.
*Update:* the file has since been **deleted in the working tree** (together with `tailwind.config.js`, correct for Tailwind v4's CSS‑first setup) — this finding is resolved pending commit (B1).
*Recommendation:* delete the file and let the Vite plugin own Tailwind; verify `build` still green.

**B24 · Fingerprint instability.** The fingerprint hashes title+source+type; any retitling changes identity, breaking dedup continuity and undermining any future stable‑id scheme (B6).
*Recommendation:* link‑based identity with title fallback; keep the hash for display/debug.

**B25 · Misleading config field.** `package.json` carries an `allowScripts` entry — a Bun/pnpm‑style field npm ignores entirely. Harmless but confusing; remove or document.

---

## 5. Backend Improvement Backlog (ordered, with acceptance criteria)

| # | Action | Findings | Acceptance criteria |
|---|--------|----------|---------------------|
| 1 | Commit the v4/shadcn working tree as two clean commits | B1 | Clean clone: `npm ci`, `typecheck`, `test`, `validate`, `build` all green |
| 2 | Truth‑up the data validator | B2, B13 | `npm run validate` exits 0 on current data and fails on a corrupted fixture |
| 3 | Pin Python env (`requirements.txt`) + document browser install | B4 | Fresh Linux box reaches a green `run_all.py --validate` from the manifest alone |
| 4 | Resolve lint gate (install eslint **or** remove script) | B5 | `npm run lint` exits 0, or no longer exists |
| 5 | Pin Node (`engines` + `.nvmrc`); remove stale `postcss.config.js`; drop `allowScripts` | B22, B23, B25 | Vercel build uses the pinned Node version; build green |
| 6 | Stable seed ids (fingerprint‑derived) + migration map | B6, B24 | User status survives two consecutive refreshes on the same opportunity |
| 7 | Preserve first‑seen `date_added` | B7 | "Added this week" remains meaningful after a refresh |
| 8 | Single supported merge path; retire or fix `merge_seeds.py` | B8 | One documented command regenerates seeds; TS2590 cannot recur |
| 9 | Repo hygiene **revised**: **track** the canonical `data/scraped_opportunities.json` (git history = the backup), ignore everything else under `data/` (backups, reports, raw dumps, `new_seed_entries.*`), untrack legacy artifacts | B9, B26 | `git ls-files data/scraped_opportunities.json` non‑empty; `git status` clean after a full pipeline run; repo growth bounded by monthly archives |
| 10 | Portability: relative paths, `date.today()`, delete dead loop | B10 | All scripts run unmodified from any checkout on Linux/macOS/Windows |
| 11 | Data‑quality fixes: no fabricated links, link‑based dedup, type mapping | B11–B13 | No `search?q=` URLs in output; same‑named distinct events both present |
| 12 | Scheduled pipeline (§6, Stage 1) | B3, B18 | Scheduled run green 3 weeks in a row with regression gate active |
| 13 | Runtime data delivery (§8) | B14, B9 | Initial JS < 300 KB; no quota errors; data updates without code deploy |
| 14 | Hardening: checkpoint/resume, retries, blocklist, enrichment cache, pytest | B15–B19 | Interrupted run resumes; blocked sources reported as `blocked`, not counted as OK |
| 15 | **File‑based data engine**: protect + track the canonical JSON, publish manifest/checksums, read‑only `/api/*`, scheduled Actions publish, Vercel deploy (§11, E1–E8) | B26, B9, B3, B2 | §11.8 smoke checklist green on the live URL; scheduled publishes run unattended with the sanity gate armed; **the site shows the complete dataset** |
| 16 | Evergreen‑deadline contract fix (utils + card + form + validator, both sides) | F1, F2, B2 | No "NaN"/"Invalid Date" anywhere; evergreen items editable; no reminder storm |
| 17 | Safe lookups + `ErrorBoundary`; migration keyed on stable ids | F8, F3, B6 | Unknown type renders a fallback chip; statuses survive renumbering |
| 18 | List virtualization/pagination + in‑memory state with debounced persistence + searchable tag combobox | F4, F5, F6, F7 | 2,000+ items: first interaction < 200 ms; no per‑interaction 1.38 MB parse |
| 19 | Router + shareable event pages with OG metadata; trusted‑domain link policy | F10, F11, F17 | Deep links + OG preview work; outbound links policed |
| 20 | Frontend quality gate: resolve `accent-foreground` token gap, delete dead code, add tests + eslint + a11y checks | F9, F16, F18, F19, F20, B5 | Token contrast ok; no unused ui files; lint + tests in CI |

---

## 6. Scheduling the Full Stack (the core issue)

### 6.1 Hard constraints

| Constraint | Value | Consequence |
|---|---|---|
| Browser requirement | Scrapling `StealthyFetcher`/patchright needs a real Chromium (~400 MB + OS libs) | Cannot run inside Vercel Functions (≈250 MB deployment bundle cap, seconds‑to‑minutes execution limits, no persistent browser, cold‑start hostile) — *verify current Vercel limits before building* |
| Full pipeline duration | ≈60–90 min (`--multi --detailed`, serial today) | Exceeds any serverless function budget; fine on a CI runner |
| Python runtime | 3.13 locally | Needs pinned deps on the runner (B4) |
| Data volume | ~2,577 items / ~2 MB JSON | Trivial to store/serve as a static asset |
| Secrets | None today | No secret management required — keep it that way |

**Conclusion: the full scrape must never run inside Vercel functions.** Only the API‑only minority (Codeforces, Kaggle, LeetCode GraphQL, USAJobs, DoraHacks, Remotive, HackerOne/Bugcrowd/Immunefi, the GitHub‑hosted Simplify list) is serverless‑viable, and it represents a small slice of the value.

### 6.2 Option comparison

| | **A. GitHub Actions only** *(start here)* | **B. Vercel Cron functions** | **C. Hybrid** *(target state)* |
|---|---|---|---|
| Runs full pipeline | ✅ ubuntu runner + browser install | ❌ only API/light sources | ✅ via Actions |
| Data freshness | **Full pipeline every 8 h** *(decided 2026‑10‑19, §11.6)* | Daily partial | Same as A via Actions, plus runtime fetch at E6 |
| Cost | Free tier: public repos unlimited minutes; private ≈4–6 h/month usage fits easily | Function invocations within free tier | Both within free tier |
| Complexity | Low — reuses existing Python code verbatim | High — pipeline must be re‑hosted | Medium, incremental from A |
| Reliability | High (artifacts, logs, retries, thresholds) | Medium | High |
| Repo churn | Data commits (or artifact upload only) | None | Artifacts only |

### 6.3 Recommended design — Stage 1 (GitHub Actions)

Workflow set for Stage 1 (one job graph, **cadence revised 2026‑10‑19 — see §11.6 for the schedule and its budget caveat**):

| Schedule (UTC) | Scope | Rationale |
|---|---|---|
| **Every 8 h** — `0 */8 * * *` (00:00 / 08:00 / 16:00 UTC; 05:30 / 13:30 / 21:30 IST) | Full `--multi --detailed --enrich` + validation + publish (§11.6) | **Decided 2026‑10‑19** — full freshness 3×/day; budget caveat in §11.6 |
| Manual (`workflow_dispatch`) | Quick `--multi` spot run (10–20 min) | investigating or recovering a single source without a full pass |
| Weekly, Sunday 03:00 | Link‑audit sample | dead‑link detection without the full‑audit cost |
| Monthly | Full link audit of every URL + dependency updates | Catches dead links/rot |

Job stages (in order): checkout → setup Python with dependency caching → install pinned deps → install Chromium + OS libraries → run the scrape (with `timeout` ≈2 h) → Python schema validation → optional link‑audit sample → regenerate seeds → npm `ci` → `typecheck` + `test` + `validate` → emit run summary (B18) with regression gate → commit data / upload artifact → Vercel redeploys automatically via its Git integration.

Guard rails: a concurrency group so overlapping runs cannot double‑write; explicit job timeout; the regression gate from B18; failure notifications (GitHub's default workflow‑failure email is sufficient to start).

### 6.4 Stage 2 (hybrid, after §8 lands)

Actions keeps doing the heavy lifting and publishes `opportunities.json` + a `version.json` manifest (version, generated_at, counts, per‑source health) as static assets. The app fetches them at runtime from the CDN — **data refreshes stop requiring code deploys entirely.** *(Decided 2026‑10‑19 as the* **second stage** *of the freshness model — rebuild‑on‑commit runs during E1–E5, the runtime fetch lands with the E6 unfreeze — §14.8 item 1.)* An optional light Vercel Cron function can refresh the API‑only subset for a "data as of" badge.

---

## 7. Vercel Deployment Plan

### 7.1 Pre‑deploy checklist (must pass on a clean clone)

1. Working tree committed (B1) — two commits: deps/config, then UI.
2. `npm ci` → green (lockfile and manifest are in sync in the working tree; keep them so).
3. `npm run typecheck` → green.
4. `npm test` → green (23/23).
5. `npm run validate` → green **after** the B2 fix.
6. `npm run build` → green.
7. Node pinned (B22); stale `postcss.config.js` removed (B23).

### 7.2 Project settings

| Setting | Value |
|---|---|
| Framework preset | Vite (auto‑detected) |
| Build command | `npm run build` |
| Output directory | `dist` |
| Install command | `npm ci` |
| Node version | pinned via `engines` |
| Environment variables | **none required** (no API keys anywhere — keep it that way; any future keys go in Vercel env + Actions secrets, never the repo) |

`vercel.json` **now exists** in the working tree (`framework: vite`, `buildCommand: npm run build`, `outputDirectory: dist`, plus a catch‑all SPA rewrite to `index.html`). The rewrite is harmless for today's single‑page app and becomes *required* once routing lands (§12 F10), so it is forward‑looking rather than wrong. Extend this file — don't create a second one — when the data‑asset cache headers from §11.4 and the freshness watchdog from §11.6/E8 arrive.

### 7.3 Rollout & rollback

- **Git integration**: production deploys from `master`; every push gets a preview deployment — use the first preview to validate the v4 migration before merging.
- **Rollback**: Vercel offers one‑click rollback to any previous deployment. Keep data commits isolated from code commits (B9) so a bad data refresh can be reverted without touching code.
- **Post‑deploy verification**: first‑load performance (current 226 KB gzip JS + CSS); first‑visit localStorage write; seed migration v8→v9 on an existing user's browser; behaviour with storage unavailable (private mode); custom domain + HTTPS.

---

## 8. Target Data Architecture

```
GitHub Actions (scheduled)
  scrape → validate → opportunities.json + version.json (manifest)
        │
        ▼
Vercel CDN / Blob  ── immutable, versioned asset URLs, ETag
        │  fetch on app load (in memory)
        ▼
App merge:  seeds (CDN)  +  user state (localStorage: id → status/notes)
             │
             └── fallback: last‑known‑good embedded snapshot if fetch fails
```

Why this is the right end state:

- **Code deploys and data refreshes decouple** — a data update is a JSON publish, not a 38k‑line TypeScript diff + full rebuild.
- **The TS2590 workaround disappears** — no giant literal array; `storage.ts` returns to ~300 lines of pure logic.
- **Bundle shrinks** — first‑load JS drops from 226 KB gzip toward <100 KB; TTI improves meaningfully on mobile.
- **Quota risk vanishes** (B14) — localStorage holds only user state (kilobytes).
- **History stays clean** (B9) — generated data leaves the repo.
- **Stable ids** (B6) become natural: the manifest id is the join key between CDN data and local user state.
- **The `.json` file *is* the database** (§11.2) — a single committed JSON + manifest: git history is the backup, `sha256` is the integrity contract, and no external service can pause, rate‑limit, rename a column or lose the dataset. *(Restated 2026‑10‑19: the database option was withdrawn — files only, and the site renders the complete file.)*

---

## 9. Phased Roadmap

| Phase | Goal | Contents | Done when |
|---|---|---|---|
| **0 — Deploy unblock** | Ship what exists | B1, B2, B4, B5, B22, B23 | Clean clone fully green + live Vercel preview |
| **1 — Data integrity** | Trust the data | B6, B7, B8, B9, B10 | Status survives refreshes; clean `git status` after a run |
| **2 — Scheduled pipeline** | Stop the manual runs | B3, B18 + Stage‑1 workflow | 3 consecutive green scheduled runs with regression gate |
| **3 — Runtime data delivery** | Decouple data from deploys | §8 architecture, B14 | Data updates publish without a code deploy; JS < 300 KB |
| **4 — Hardening** | Survive the wild | B15–B17, B19, B24 | Resume works; blocked ≠ failed; pytest coverage on `base.py` |
| **5 — Deployed data engine (JSON only)** | Fresh data, live site, complete catalog shown, no database | §11 milestones **E1–E8** — F1/F2 land as the **E6** controlled unfreeze (before the E7 deploy), F3 is fixed data‑side at E3, F8 is substituted by the sanity gate | §11.8 smoke checklist + §12.5 criteria green on the live URL; scheduled publishes unattended |

---

## 10. Operational Runbooks

**Manual full refresh (local, current state)**
1. `python scripts/scrapers/run_all.py --multi --detailed` → `data/scraped_opportunities.json`
2. `python scripts/scrapers/run_all.py --validate` (expect 0 errors)
3. `python scripts/regenerate_seeds.py` (bumps `SEED_VERSION`, rewrites `SEED_DATA`)
4. `npm run validate` → must be green (after B2 fix)
5. `npm run typecheck && npm test && npm run build`
6. Commit **only** the data/config files; push → Vercel redeploys.

**Triage**

| Symptom | Likely cause | First action |
|---|---|---|
| Source returns 0 items | Selector rot or layout change | Inspect page; update `sources.json` selectors or the built‑in scraper |
| Source returns 0 with HTTP 403/429 | Bot protection | Mark source `blocked` (B16); consider API alternative or reduce frequency |
| `npm run validate` red | Data/validator mismatch | Compare against the three known rules (B2) before blaming the data |
| Deploy red, local green | Uncommitted state or Node version drift | B1 / B22 |
| Item count drops >40 % | Mass source failure | Check run summary per‑source counts; re‑run with `--verbose` |

**Adding a source** — prefer the `sources.json` registry (no code; CSS selectors) for simple listing pages; add a built‑in scraper only when the site needs JSON‑LD/GraphQL parsing. Acceptance: new source appears in per‑source counts and the validator stays green.

**Data rollback** — revert the data commit (data commits stay isolated, B9); Vercel redeploys the previous data automatically.

---

## 11. Deployed Data Engine — File‑Based Plan (JSON only, no database)

> **Superseded plan (2026‑10‑19):** an earlier revision of this section proposed **Supabase** (managed PostgreSQL + Auth + Row‑Level Security + Storage) with user accounts and user‑created events. **Withdrawn on request.** The `supabase/` scaffold was deleted and the globally installed CLI uninstalled; no project, key, migration or account was ever created. What follows is the replacement plan: **one JSON file as the database, a scheduled engine that keeps it fresh, and a read‑only site that shows the complete dataset.**

Answering the two original questions in the new model:

- **What DB?** → **none.** The only data store is **`data/scraped_opportunities.json`** (plus a companion `data/manifest.json` holding counts, provenance and `sha256`). Git history is the backup, the Vercel CDN is the read layer. Zero keys, zero cost, nothing that can pause or expire — and the pipeline already emits exactly this format.
- **What API calls?** → **read‑only only.** Two static JSON assets plus Vercel functions under `/api/*` (§11.4). There are **no write endpoints at all**, so there is no auth, no JWT, no RLS — and no way for a visitor to alter the dataset.

### 11.1 Stack (revised)

| Layer | Choice | Role |
|---|---|---|
| Dataset — **the only store** | **`data/scraped_opportunities.json`** + `data/manifest.json`, **tracked in git** | canonical, complete, diffable, checksummed, restorable |
| Engine (the scheduled backend) | **GitHub Actions** (cron) | scrape → validate → sanity gate → publish; the **only writer** of the JSON (§11.6) |
| Read API | **Vercel Functions** `/api/*` — read‑only, CDN‑cached | filtered/paginated reads over the JSON, health, manifest, stats, OG images |
| Bundled copy | `SEED_DATA` snapshot in `storage.ts` | instant first paint + offline fallback — same complete data, never a reduced subset |
| Hosting | **Vercel** (Vite preset, `dist`) | static SPA + functions + Git‑triggered deploys (§7) |
| Visitor state | **browser only** (localStorage, kilobytes) | status/notes per visitor — never uploaded, never mixed into the JSON |

**Withdrawn entirely:** Supabase, Postgres, RLS, auth, accounts, `profiles`/`events`/`rsvps`/`saved`, service‑role keys, `IMPORT_SECRET`, the Supabase CLI and its scaffold. **Nothing in this plan requires a login, a key, or a paid service** — the engine is real backend, it just runs on files instead of a database.

### 11.2 The data contract — one JSON file, complete

**Completeness rule (explicit):** the JSON holds **every validated item** (**2,588** as of 2026‑10‑19) and the site must be able to **show all of them** — searchable, filterable, sortable, paginated/virtualised for speed, but **never truncated, sampled or "top‑N"**. Every copy of the data (bundled snapshot, browser cache, export) is the **same complete set**, so a visitor with no network at all still sees the whole catalog.

| Path | Role | Tracked in git |
|---|---|---|
| `data/scraped_opportunities.json` | **canonical dataset — the only data store**: an array of opportunity objects, exactly the shape the app already consumes | ✅ **yes — this is a change: today it is gitignored, which is the protection gap (B9/B26)** |
| `data/manifest.json` | `schema_version`, `generated_at`, `item_count`, `type_histogram`, `per_source_counts`, `rolling_count`, `sha256`, pipeline `run_id`, `duration_s`, `git_commit`, `validator_version`, `seed_version` | ✅ yes |
| `data/reports/publish-YYYYMMDD.md` | publish report: validation result + diff (new/removed/changed, per source) | ✅ yes |
| `data/scraper_health.json` | per‑source health map (feeds `/api/sources`) | ✅ yes |
| `public/data/manifest.json` | published pointer the app reads first (cache‑busting) | ⬜ generated at publish |
| `public/data/opportunities.<sha8>.json` | published copy, **byte‑identical**, immutable filename | ⬜ generated at publish |
| `data/backups/scraped_YYYYMMDD_HHMMSS.json` | rotation: last 7 daily + last 8 weekly (and/or Actions artifacts, 90‑day retention) | ⬜ ignored |
| `src/lib/storage.ts` → `SEED_DATA` | bundled snapshot used only for first paint / offline fallback | ✅ yes |

**Shape:** the file stays a plain **array** (no wrapper object), so nothing about the current app breaks; all metadata lives in the manifest.
**Fields:** `id`, `title`, `type`, `source`, `link`, `deadline`, `eligibility`, `tags[]`, `status`, `notes`, `date_added`, plus optional `location`, `prize_pool`, `participants`, `organizer`, `duration`, `quality_score`.
**Contracts:** `type ∈ {Hackathon, Internship, Certification, Competition}`; **`deadline: ''` means rolling/evergreen** (the rule both sides must honour — B2/F1); `link` is a valid `http(s)` URL or empty and is **never fabricated** (B11).
**Identity:** stable **fingerprint‑hash ids** (B6/B24) — the join key between the published JSON and a visitor's local state.
**Integrity:** `sha256` of the exact bytes, computed **after** validation, recorded in the manifest, verified by `/api/health` and by the app when it fetches.

### 11.3 Protection model — "make sure to protect it" (12 controls)

| # | Control | Failure it prevents |
|---|---|---|
| 1 | **Track the canonical JSON in git** (remove it from `.gitignore`) | today the dataset exists only on one Windows machine as an ignored file — a disk loss erases the project's entire value |
| 2 | **Weekly lightweight tag** `data-YYYY.MM.DD` + **monthly GitHub Release** with the JSON attached | long‑term retention without multiplying repo bloat |
| 3 | **Atomic writes** in every writer: temp file → `fsync` → `os.replace` | a killed/crashed run truncating or half‑overwriting the dataset |
| 4 | **Validate‑before‑publish**: Python schema validation + `run_all.py --validate`, then `npm run validate` (needs B2) | publishing data that breaks the app's types |
| 5 | **Sanity/regression gate**: total count within **±20 %** of the previous manifest, per‑source within ±50 %, no collapse to 0, non‑degenerate type histogram | a broken scraper silently replacing 2,588 good rows with 300 |
| 6 | **Single writer**: Actions `concurrency: {group: data-publish}`, `git pull --rebase` + retry, refuse to publish on a dirty tree | two scheduled runs clobbering each other; force‑pushes |
| 7 | **Checksums**: `sha256` recorded in the manifest *after* validation, verified by `/api/health` and by the app | silent corruption/truncation between publish and read |
| 8 | **Backups + a tested restore drill** (revert commit → tag → artifact → Release) | discovering the restore path doesn't work during an outage |
| 9 | **Bounded repo growth**: `data/*` ignored except the tracked canonical file, manifest and reports; `linguist-generated` on the dataset; monthly squash decision point | a 1.9 MB weekly diff making the repo unpleasant to use |
| 10 | **No secrets by construction**: the engine needs only the automatic `GITHUB_TOKEN`; the publish job gets `contents: write` and nothing else | the entire credential‑leakage class of incident disappears |
| 11 | **Source quarantine**: `blocked` ≠ success (B16), link health recorded per source, alert only after N consecutive failures | a bot‑blocked source being reported as "0 results, fine" forever |
| 12 | **Immutable published asset**: filename carries the `sha8`, `Cache-Control: max-age=31536000, immutable`; the app never guesses a filename | stale or mixed data after a read that straddled a publish |

### 11.4 API inventory — 9 read‑only functions + 2 static assets (no auth, no writes)

**Static assets (served straight from `public/`, no function needed):**

| Path | Purpose | Cache |
|---|---|---|
| `GET /data/manifest.json` | pointer the app reads first: current `sha8`, counts, `generated_at` | `s-maxage=300, stale-while-revalidate=86400` |
| `GET /data/opportunities.<sha8>.json` | the **complete** dataset (bulk load, offline cache, download) | `max-age=31536000, immutable` |

**Vercel functions (`/api/*`, Node runtime, all `GET`, all reading the same JSON):**

| Method | Route | Purpose | Cache |
|---|---|---|---|
| GET | `/api/health` | deploy + data‑freshness smoke: age, counts, `sha8`, last publish status, commit | `no-store` |
| GET | `/api/manifest` | same manifest, CORS‑enabled for the app | `s-maxage=300` |
| GET | `/api/opportunities` | filtered + paginated reads over the JSON: `q`, `type`, `source`, `tag`, `deadline_within`, `status=rolling`, `sort`, `page`, `page_size≤100` | `s-maxage=3600, swr=86400` |
| GET | `/api/opportunities/:id` | single record — shareable link | `s-maxage=3600` |
| GET | `/api/stats` | type/source histograms, rolling vs dated, closing‑soon counts (feeds Hero/Stats) | `s-maxage=3600` |
| GET | `/api/sources` | source registry + health map (`data/scraper_health.json`) | `s-maxage=3600` |
| GET | `/api/report/latest` | last publish report (validation + diffs) — an ops page anyone can audit | `s-maxage=300` |
| GET | `/api/og?title=…&type=…` | dynamic OG image for shareable links (F11) | `s-maxage=86400` |
| GET | `/api/export?format=csv\|ics\|json` | server‑side export of the filtered set (moves F15's export off the main thread) | `s-maxage=3600` |

On a first screen the app uses at most **three** requests: `/data/manifest.json` → `/api/opportunities` (first page) → `/api/stats`; the full JSON is fetched in the background for the local cache.

**Conventions:** JSON in/out; `{error, code}` error shape; every query param validated and clamped server‑side using **the same rules as the data validator** (`page_size ≤ 100`, `type` must be in the enum, dates empty or `YYYY-MM-DD`); 400 on bad params, 404 on unknown id, 429 via Vercel WAF rate limits; **no POST/PATCH/DELETE route exists anywhere**. If a submission feature is ever wanted it must be a PR/Issue flow — never a write to the dataset (§13 item 8).

### 11.5 How the app consumes the JSON (and still shows the complete data)

**No auth flow exists any more** — there is nothing to log in to. What replaces it is a small data‑loading ladder:

1. Fetch `/data/manifest.json` (small, cached) → compare `sha8` + `item_count` against the bundled snapshot's own constants.
2. If newer: fetch `/api/opportunities?page=1&page_size=100` for the first screen, and pull `/data/opportunities.<sha8>.json` in the background to cache **the complete set** locally in **IndexedDB** — not localStorage, which keeps B14/F4/F6 solved at the same time.
3. Merge visitor state (status, notes, first‑seen `date_added`) by stable id from localStorage — kilobytes only.
4. **Fallback ladder:** API 200 → cached complete JSON (IndexedDB) → bundled `SEED_DATA` snapshot. The board must render with **zero network calls** (private mode, offline, function outage) — and in every rung it is the *complete* catalog, not a sample.
5. Rendering the complete set: keep filters/sort/search client‑side on the full array (fast — 2.6k items), use the paginated API only for the initial paint; virtualise the list (§12 F4) so "all of it" stays usable.
6. Never write the catalog back to localStorage (B14); never block first paint on the network (F4).

### 11.6 The engine — scheduled, unattended, always running

Three workflows in `.github/workflows/`, all on the repository's clock (UTC; IST in brackets). **Cadence decided 2026‑10‑19: a full pipeline run every 8 hours.**

| Workflow | Trigger | Command | Budget |
|---|---|---|---|
| `verify.yml` | `push`, `pull_request`, `workflow_dispatch` | `scripts/check_freeze.py` → `npm ci` → typecheck → test → build → `npm run validate` → Python schema validation | 3–6 min |
| `scrape-full.yml` | `schedule: "0 */8 * * *"` — 00:00 / 08:00 / 16:00 UTC (05:30 / 13:30 / 21:30 IST) + manual | `run_all.py --multi --detailed --enrich --validate` → publish | 60–90 min |
| `scrape-quick.yml` | `workflow_dispatch` only (no schedule) | `run_all.py --multi --validate` → publish | 10–20 min |

> **⚠️ Budget check (the one open sub‑item on this decision):** 3 full runs/day × ~75 min ≈ **6,800 Actions minutes/month**. The repo is currently **private**, where the free tier allows **2,000**. One of these must hold before E5 goes live: **(i)** make the repo **public** at deploy — unlimited minutes, and recommended anyway for a public catalog; **(ii)** upgrade to a paid plan; or **(iii)** degrade the cadence to *every‑8‑h quick* + *weekly full* (~1,400 min/month). Default if nothing changes: the quota is hit mid‑month, remaining runs queue, and the E8 freshness watchdog fires — which is the intended alarm.

Every scrape run is the same guarded sequence:

```
checkout → setup-python 3.13 (cached) → pip install -r requirements.txt
  → restore+install Chromium (ms-playwright cache)
  → run the pipeline            → write data/scraped_opportunities.json (atomic)
  → Python schema validation    → FAIL = stop, nothing is published
  → sanity/regression gate      → FAIL = stop + refresh a tracking Issue
  → write data/manifest.json (counts + sha256) + data/reports/publish-*.md
  → regenerate the bundled snapshot (bump SEED_VERSION, same complete data)
  → rotate backups → weekly tag / monthly Release
  → commit & push (single writer, rebase-retry)        → triggers a Vercel rebuild
  → upload artifacts (raw JSON + report, retention 90 days)
  → GET https://<prod>/api/health → assert age < 12 h (8 h cadence + slack) and sha8 matches
```

Guard rails: `timeout-minutes` 120 (scheduled full) / 30 (manual quick); `concurrency: {group: data-publish, cancel-in-progress: false}`; **per‑source minimum interval ≈ 4 h** (at 3 runs/day, skip a source whose last successful fetch is newer, and skip `--enrich` re‑work on unchanged items) so the cadence never degenerates into hammering; per‑source `continue-on-error` **inside** the pipeline so a dead source can't fail the job (B16), while the job itself fails on validation, sanity‑gate or post‑publish health‑check failure only. Failures open **one** tracking Issue (`data-pipeline-alert`) instead of spamming.

Caching that pays for itself: pip (~2 min), npm, and above all **`~/.cache/ms-playwright`** (~150 MB of Chromium that would otherwise be re‑downloaded every run).

Publishing path **(decided 2026‑10‑19 — both, staged)**: **stage 1 = (a)** commit to `main` → Vercel rebuild (~1–2 min) for all of E1–E5; **stage 2 = the runtime fetch** (manifest‑first ladder, §11.5) lands with the **E6 unfreeze**, after which freshness needs no rebuild at all. Options not taken: **(b)** a `data` branch the app fetches directly, **(c)** doing both from day one. Rationale: nothing under `src/` can consume a runtime source until the freeze lifts — §14.1.

### 11.7 Files to add / change (written at execution time, not now)

| Path | Change |
|---|---|
| `.gitignore` | **un‑ignore `data/scraped_opportunities.json`**; keep ignoring backups, reports, raw dumps, `new_seed_entries.*` |
| `data/manifest.json` | new — counts, histograms, provenance, `sha256` |
| `scripts/publish_dataset.py` | new — validate → sanity gate → manifest → atomic write → backup rotation → snapshot regeneration → publish report |
| `scripts/scrapers/*.py` | atomic writes; relative paths + `date.today()` (B10); no fabricated links (B11) |
| `scripts/validate-data.mjs` | fix the three stale rules (B2) — this becomes the publish gate |
| `.github/workflows/{verify,scrape-quick,scrape-full}.yml` | new — the engine (§11.6) |
| `api/{health,manifest,opportunities,opportunities/[id],stats,sources,report/latest,og,export}.ts` | new — read‑only routes (§11.4) |
| `src/lib/api.ts` | new — typed fetch wrapper, manifest‑first, fallback ladder (§11.5) |
| `public/data/` | generated at publish (immutable asset) |
| `vercel.json` | extend: cache headers for `/data/*` and `/api/*`; the SPA rewrite is already there |
| `docs/ENGINE.md` | new — runbook: local run, publish, restore, alert response |

**No secrets, no env vars, no accounts anywhere in this list.** Vercel needs no variables at all; Actions uses only the automatic `GITHUB_TOKEN`.

### 11.8 Deployment steps (Actions ↔ Vercel) and smoke checklist

1. Land the prerequisites: commit the v4/shadcn working tree (B1), fix the validator (B2), pin Node (B22), add `requirements.txt` (B4).
2. Track the JSON + add the manifest/publish script (§11.7) → first commit of the canonical dataset (**2,588** items as of 2026‑10‑19; never hardcode the count — read the file).
3. Add the three workflows; run `scrape-quick` once manually → confirm it commits data + report and the post‑publish health poll passes.
4. Add the read‑only `/api/*` routes and the `public/data` copy step; set cache headers in `vercel.json`.
5. Vercel: import the repo (Vite preset, `dist`), pin Node → deploy a **preview**, run the checklist below, then promote to production.
6. Enable the schedules (**full pipeline every 8 h**, `0 */8 * * *`, plus manual‑only `scrape-quick`) and the weekly tag / monthly Release job.
7. Watchdog: a small daily freshness check (Actions step or Vercel Cron) that fails loudly if data is older than 48 h. *There is no database, so there is nothing to keep alive — no pause problem exists.*

**Smoke checklist (all must pass on the live URL):**

| # | Check | Expected |
|---|---|---|
| 1 | `GET /api/health` | 200; `age_hours` < 24; `item_count` and `sha256` match the manifest |
| 2 | `GET /data/manifest.json` | 200, `s-maxage` present, counts sane |
| 3 | `GET /data/opportunities.<sha8>.json` | 200, `immutable`, row count = manifest, `sha256` recomputes byte‑for‑byte |
| 4 | `GET /api/opportunities?page_size=10000` | 400 — clamped and validated, no crash, no OOM |
| 5 | `GET /api/opportunities?status=rolling` | only empty‑deadline items; UI shows *Rolling*, never "NaN days left" (F1) |
| 6 | Any write attempt (`POST /api/opportunities`) | 404/405 — **no write surface exists** to abuse |
| 7 | Load the board with the network blocked | bundled snapshot renders the **complete** catalog (fallback ladder, §11.5) |
| 8 | Re‑run the publish script on unchanged data | no diff, no new commit, no duplicate rows (idempotent) |
| 9 | Restore drill: revert the latest data commit | the previous dataset is served again within one deploy |

### 11.9 Security & integrity gates

- **No credentials exist to leak** — no API keys, no service‑role key, no DB password, no session tokens (the audit grep‑verified this; keep it that way). Nothing in the browser is privileged because nothing is privileged at all.
- Actions publish job: `permissions: contents: write` only; no `pull_request_target`; third‑party actions pinned by commit SHA.
- Every query param validated and clamped server‑side; WAF rate limits; no visitor input ever reaches the filesystem or a shell.
- The dataset is **read‑only from the internet**: the only writer is the scheduled job on a runner we control, and it can only push commits to `data/**`.
- Outbound scraped links: `rel="noopener noreferrer"` plus a trusted‑domain policy/interstitial (F17) before any public launch.
- Integrity = `sha256` + count gates (§11.3), with `/api/report/latest` exposing the last validation run so anyone can audit the pipeline's honesty.
- No PII in the catalog (audit found none), and none added later: there is no user input path at all.

### 11.10 Milestones (execution order — work proceeds exactly per this table)

| # | Milestone | Depends on | Acceptance |
|---|---|---|---|
| **E1** | **Protect the data**: track the canonical JSON, manifest, atomic writes, backup rotation, `.gitignore` revision | — | `git ls-files data/scraped_opportunities.json` non‑empty; restore drill passes |
| **E2** | **Truth‑up the validator** (B2) + the sanity/regression gate | E1 | `npm run validate` exits 0 on current data **and** rejects a corrupted/short fixture |
| **E3** | **Publish script**: manifest + `sha256` + `public/data` asset + report | E1, E2 | one command yields dataset + manifest with matching checksums |
| **E4** | **Read‑only API** + cache headers (`health`, `manifest`, `opportunities`, `stats`, `og`, `export`) | E3 | smoke rows 1–5, 7 green on the preview URL |
| **E5** | **The engine**: `verify` + `scrape-full` (every‑8‑h schedule) + `scrape-quick` (manual) workflows | E2, E3 | 3 consecutive green scheduled runs at the decided cadence; bot commit carries a report; re‑run is a no‑op |
| **E6** | **Controlled unfreeze #1** — one allowlisted `src/` patch: **F1/F2 fixes** (evergreen *Rolling* presentation + reminder guard) **and stage‑2 runtime data fetch** (manifest‑first ladder, §11.5) | E3, E4, E5 | `check_freeze.py` green with exactly one allowlist entry; F‑1/F‑2 criteria (§12.5) pass; offline fallback still renders the complete catalog; freshness no longer needs a rebuild |
| **E7** | **Production deploy** | E4, E5, E6 | **all 9 rows of §11.8** green on prod; F‑1/F‑2 green; complete catalog reachable; first‑load JS < 300 KB after the runtime fetch lands |
| **E8** | **Watchdog + retention**: freshness alert (`age < 12 h`), weekly tags, monthly Release archive + **monthly squash** of the dataset history | E5 | data age never exceeds 12 h unnoticed; 3 tags + 1 archive exist; repo size growth bounded |

**Status (2026‑10‑19):** E1 not started. **All four blocking decisions are settled (§14.8):** staged freshness (rebuild now, runtime fetch at E6), full pipeline every 8 h, unfreeze F1/F2 before the first public deploy, canonical JSON tracked in git with a monthly squash. The Supabase track was started and then **withdrawn the same day** — the `supabase/` scaffold (created earlier today) was deleted and the globally installed CLI uninstalled; the working tree contains no trace of it. `frontend/PLAN.md` still describes Supabase and needs the corresponding rewrite. **One open sub‑item:** repo visibility (private free tier = 2,000 Actions min vs ~6,800 needed at the chosen cadence — see the budget box in §11.6).

### 11.11 Risks & mitigations

| Risk | Mitigation |
|---|---|
| Repo grows ~1.9 MB per refresh | only the canonical JSON is tracked; weekly tags + monthly Release archives; explicit monthly squash decision point |
| Bot commits clash with human commits | single‑writer concurrency group + `pull --rebase` retry; data commits touch `data/**` only |
| A broken scraper publishes a tiny dataset | the ±20 % sanity/regression gate (§11.3 #5) blocks the publish and opens an Issue |
| Actions minutes (private repo) | ≈15 min/day + ≈90 min/week ≈ 800 min/month → inside the 2,000 free minutes; unlimited on a public repo |
| Chromium re‑download every run | `ms-playwright` cache → ~2 min instead of ~6 |
| Vercel free‑tier limits | static + cached reads only; no writes, no DB, no cron needed for correctness |
| Data corruption or truncation | atomic writes + `sha256` + a **tested** restore drill (revert → tag → artifact → Release) |
| Scraped links rot | link‑health job (B16/B17) records rot per source; UI marks dead links |
| "No backend" misreading | the **engine is the backend**: scheduled, versioned, monitored, with a publish gate — it simply runs on files instead of a database |
| Fallback drift (snapshot ≠ published file) | the snapshot is regenerated by the same publish command, so all three copies come from one write |

---

## 12. Frontend Audit (read‑only) — Findings & Prototype Requirements

> Added on request (*"check on the frontend, working rule"*): the same working rule applies — **only this file is written**; no source file was changed. Method: full read of every view, hook, util and shadcn component, plus **execution of the real bundled modules** (`src/utils/date.ts`, `src/lib/storage.ts`) to verify behaviour and measure payloads.
>
> **Related file:** `frontend/PLAN.md` (author's own frontend plan — stack: Vite/React 18/TS/Tailwind v4/shadcn/**React Router**/Vercel; phases ticked as if done). It is the frontend execution counterpart to this section. **Read it as historical:** its Supabase, auth, account and DB‑backed‑dashboard phases were withdrawn on 2026‑10‑19 along with §11's database plan, and those phases are exactly the ones requiring `src/` changes now under freeze (§14.6). Note **F21** before trusting any tick.

### 12.1 Verified numbers (measured 2026‑10‑19, `SEED_VERSION 9`)

| Metric | Value |
|---|---|
| Seeds in `SEED_DATA` | 2,577 |
| localStorage payload written on first visit | **1.38 MB** (1,444,140 utf‑8 bytes) |
| Cards rendered on first paint (dashboard, no filters) | **1,940 active** (+ 637 behind the archive toggle) |
| Seeds with an **empty deadline** | **1,718** (66.7 %) |
| Deadlines already in the past | 637 |
| Unique sources / unique tags | 75 / **1,092** |
| Production JS bundle | 1,559 kB (226 kB gzip) |
| Bundle of one dependency chain | React 18 + Radix + Tailwind v4 |

### 12.2 Findings

| ID | Sev | Area | Finding |
|----|-----|------|---------|
| F1 | High | Data contract | 1,718 evergreen items render as **"NaN days left"**; `TBD` renders **"due Invalid Date"**; the edit form **blocks saving** them ("Deadline is required") |
| F2 | High | Notifications | Reminders fire for **every** evergreen item — `days < 0 \|\| days > 2` passes `NaN` → notification storm |
| F3 | High | Migration | Seed renumbering (B6) makes stored user edits/content drift; a stale record can outlive its real seed |
| F4 | Medium | Performance | No virtualization/pagination — **1,940 cards** + a 1.38 MB parse on first paint |
| F5 | Medium | State | Every mutation re-parses (read) and re-stringifies (write) the whole 1.38 MB list on the main thread |
| F6 | Medium | Resilience | Quota/private‑mode failure surfaces as a **full‑screen "Couldn't load your data"** error instead of read‑only mode |
| F7 | Medium | Usability | Tag filter renders **1,093 options** in one non-searchable Select; source filter 76 |
| F8 | Medium | Robustness | No ErrorBoundary + exhaustive `TYPE_META`/`STATUS_META` lookups → a new backend type (B12) **white‑screens the app** |
| F9 | Medium | Theme | shadcn components use `bg-accent`/`text-accent-foreground`; the theme repurposed `accent` as brand indigo and defined **no `accent-foreground`** → focus/hover states are off‑theme and low‑contrast |
| F10 | Medium | Architecture | No router — `viewMode` state only; no deep links, shareable event URLs or per‑route code splitting (blocks §11 event pages) |
| F11 | Low | SEO | No OG/Twitter/social metadata, no sitemap/robots; nothing to preview when an event link is shared |
| F12 | Low | Dates | Hardcoded `en-IN` locale and `T23:59:59` parsing baked into formatting/urgency maths |
| F13 | Low | Features | "Newly added" / "this month" features depend on `date_added`, which B7 resets every scrape (all 2,577 would count "added today") |
| F14 | Low | Search | Search matches **title only** — not tags, source, organizer or eligibility |
| F15 | Low | Export | One `copied` flag serves both clipboard items; no failure feedback; export ignores active filters |
| F16 | Low | Hygiene | `TYPE_COLORS` / `TYPE_ICONS` / `STATUS_COLORS` unused (superseded by `lib/meta.ts`); `ui/{tabs,tooltip,separator,badge,card}.tsx` unused |
| F17 | Low | Security/UX | Scraped links opened raw (`rel="noopener noreferrer"` only) — a public site needs a trusted‑domain policy |
| F18 | Low | Quality | No frontend tests, no ESLint (B5), no a11y automation; 4 Google font families from CDN with no preload |
| F19 | Low | A11y | Severity conveyed by colour alone in Hero/Stats; toasts can't be dismissed; Escape handled twice (App + Radix) |
| F20 | Info | Design system | The uncommitted shadcn migration (B1) mixes stock shadcn components with editorial custom ones — the boundary must be decided before §11 forms are built |
| F21 | High | Doc vs state | `frontend/PLAN.md` ticks **all** phases (scaffold, Supabase wiring, auth, landing, DB‑backed dashboard, `vercel.json`, README) yet `frontend/` currently contains **only `PLAN.md`** — treat it as intent, and verify each item against the tree before marking anything done. **Update 2026‑10‑19:** the Supabase/auth/dashboard phases are now *withdrawn* (§11) — the file needs its Phase‑1+ rewritten around the file‑based model before it can serve as a plan |

### 12.3 Detail on the High findings

*(F1–F3 below; F21 is explained in its row above — before any milestone is ticked in `frontend/PLAN.md`, verify the artefact exists in the tree, exactly as §11.8/§12.5 do for the live deployment.)*

**F1 — Evergreen items break four surfaces at once.** Verified by executing `src/utils/date.ts` against the real data shape:

| Input | `daysBetween` | `getDaysLabel` | `getUrgency` | `formatDate` | form save |
|---|---|---|---|---|---|
| `''` (1,718 items) | `NaN` | **"NaN days left"** | `safe` | `''` | **blocked** |
| `'TBD'` | `NaN` | **"NaN days left"** | `safe` | **"Invalid Date"** | **blocked** |
| `'2026-12-31'` | `73` | "73 days left" | `safe` | "31 Dec 2026" | ok |

So: the badge says "NaN days left", the "due …" line is empty, the item is coloured *safe* (it is neither), it is invisible to the "due within 7/14/30 days" filters and to Hero/Stats "upcoming/overdue" counters, and opening it in the edit dialog makes it unsaveable. Root cause is the same contract gap as **B2** (validator requires a deadline the data doesn't have); the fix must land on both sides together.

**F2 — Notification storm.** Mirroring the exact guard from `useReminders.ts`:

| `days` | `days < 0 \|\| days > 2` | Effect |
|---|---|---|
| `NaN` | `false` | **notification fires** ("due in NaN days") |
| `0 / 1 / 2` | `false` | fires (correct) |
| `5 / -3` | `true` | skipped (correct) |

With reminders enabled, all 1,718 evergreen items pass the guard, producing one notification each (browser‑capped but still a flood, once per day per item via the `id:date` key).

**F3 — Migration drift.** `loadOpportunities()` (storage.ts:39655‑39682) on a version bump: drops `seed_*` ids no longer present, replaces same‑id records only when `status === 'Not Started'`, and adds only ids that don't exist yet. Because `regenerate_seeds.py` renumbers positionally, an id can now point at a *different* opportunity: a user's edited/"Applied" record keeps its stale content and id while the current item at that id is never added (its id already exists). Result: duplicated‑looking, stale or missing rows — and status attached to the wrong opportunity. Fix belongs with **B6** (stable fingerprint ids + migration keyed on fingerprint).

### 12.4 What the frontend must gain for §11 (prototype requirements)

> **Every row below needs a `src/` change.** Decision 2026‑10‑19: **F1/F2 + the data layer ship at milestone E6** (one allowlisted patch, before the E7 production deploy); the rest park until a later unfreeze (§14.6). `src/`‑free substitutes, where any exist, are noted.

| Need | Reason | Unfreeze gate |
|---|---|---|
| "Rolling / no deadline" presentation (badge + sorting + filters) | F1 — removes *NaN days left* on 1,718 cards | **E6 — decided** (with F2; the only visible defect class, §14.6) |
| Reminder guard hardened (`Number.isFinite`) | F2 | **E6 — decided** (same patch as F1) |
| `ErrorBoundary` + safe meta lookups with fallbacks | F8 — new types must never white‑screen | Later unfreeze (post‑E7); *substitute now:* `sanity_gate.py` blocks unknown `type` values before they reach the bundle |
| Router with `/events/:id` + OG/Twitter meta per item | F10/F11 — shareable URLs (the `/api/og` + `/api/opportunities/:id` routes already exist from E4) | Later unfreeze (post‑E7) |
| Server data layer (TanStack Query or SWR): pagination, caching, optimistic mutations | F4/F5 — stop re‑parsing 1.38 MB per interaction | **E6 — decided** (rides the stage‑2 runtime fetch, §14.8 item 1) |
| Windowed/paginated lists | F4 | Later unfreeze (post‑E7) |
| Shared form schema matching the API contract: title required, **deadline optional**, type enum | F1 + B2 | E6 (with F1) |
| Searchable tag/source comboboxes (search + top‑N) | F7 | Later unfreeze (post‑E7) |
| Quota/private‑mode read‑only fallback | F6 | **E6 — decided** (IndexedDB cache path, §11.5) |
| Trusted‑domain policy for outbound scraped links | F17 | Before the E7 public launch — enforceable data/`api`‑side |
| Design‑system decision (stock shadcn vs editorial) + token gap fixed | F9/F20 | Later unfreeze (post‑E7) |
| ~~Auth context/provider + protected routes~~ | ~~§11.4 session flow~~ | **Deleted** — no auth exists in the revised §11 |

### 12.5 Frontend acceptance criteria (extends §11.8)

| # | Check | Expected |
|---|---|---|
| F‑1 | Search an evergreen item, edit it, save | Saves; shows *Rolling*, never "NaN"/"Invalid Date" |
| F‑2 | Enable reminders with evergreen items present | Zero notifications for empty deadlines |
| F‑3 | Force an unknown `type`/`status` value | Fallback chip renders; app does not crash |
| F‑4 | Load dashboard with 2,000+ items | First interaction < 200 ms (virtualized or paginated) |
| F‑5 | Change one status | No full‑list parse/stringify on the main thread; UI updates instantly |
| F‑6 | Open the tag filter | Searchable combobox, not a 1,093‑option list |
| F‑7 | Share an event URL | Deep link opens the event with an OG preview |
| F‑8 | Private mode / storage full | App loads read‑only instead of a full‑screen error |
| F‑9 | Keyboard‑only pass (tab/enter/esc, focus visible) | All §11 flows reachable, contrast ok |

---

## 13. Open Decisions (need your call)

> The four decisions that **blocked execution** were **settled on 2026‑10‑19** — answers and consequences recorded in **§14.8** (staged freshness, full pipeline every 8 h, F1/F2 unfreeze at E6, canonical JSON tracked + monthly squash). The list below is **non‑blocking** — each can be settled as its milestone arrives. Items about Supabase region, auth providers, DB import timing and schema size were removed on 2026‑10‑19 when the database plan was withdrawn. **One open sub‑item:** repo visibility for Actions minutes (§11.6 budget box).

1. **Stable‑id scheme** — fingerprint‑hash ids (recommended; continuous with existing dedup, and also the F3 fix) vs source+slug ids (human‑readable).
2. **Type union** — add `Scholarship`/`Fellowship` to `Opportunity`? Backend can stage correct strings now; the union change is a frontend touch (frozen `src/`).
3. **`merge_seeds.py`** — retire it (recommended; it emits the pre‑v4 format that breaks TS2590) or update it to the current entry format.
4. **Lint** — install + configure eslint (recommended for CI) or delete the `lint` script.
5. **Routing** — *decided by `frontend/PLAN.md`: **React Router*** (SPA rewrite already in `vercel.json`). Confirm at the first `src/` unfreeze.
6. **Server data layer** — TanStack Query (recommended: caching + optimistic updates) vs SWR vs hand‑rolled fetch wrapper (F4/F5) — decided when the freeze lifts.
7. **Rendering/SEO for the public site** — keep the Vite SPA + prerender plugin (fastest to ship) vs move to Next.js/Remix when per‑item pages and OG previews matter (F11).
8. **Accounts & submissions scope** — stay **read‑only** (catalog + localStorage state per visitor, recommended, matches the revised §11) vs add a PR/Issue‑based submission flow later (contributors propose entries as pull requests — never a write route).

---

## 14. Repository Model — Complete Code Base (`src/` frozen)

> Derived from the live tree on 2026‑10‑19 (root: 14 files, `scripts/` 84 scrapers + 9 utility files, `data/` 8 files, `docs/` 14 markdowns, `tests/` 1 file, `public/` 1 file, no `.github/`, no `api/`).
> **Hard constraint for every milestone that follows: nothing under `src/` may be created, edited, moved or deleted.** Everything outside `src/` is fair game. §11.7 and §14.5 list the exact files each milestone touches; if a step appears to need `src/`, it is either parked (§14.6), a **generator write** (Exception A, §14.1), or the single allowlisted **E6 patch** (Exception B).

### 14.1 The freeze, and the one exception

| Rule | How it is enforced (not just promised) |
|---|---|
| No hand‑edited file under `src/` | `scripts/check_freeze.py` runs in `verify.yml` on every push: `git diff --name-only <base>...HEAD -- src/` must be **empty except `src/lib/storage.ts` and paths listed in `docs/FREEZE_ALLOWLIST.md`** — exit 1 otherwise |
| **Exception A:** `src/lib/storage.ts` may change, but **only** written by `scripts/regenerate_seeds.py` | the generator is the sole writer; `verify.yml` also runs `typecheck` + `npm test` (23 tests import the real bundled module) so a malformed write cannot merge |
| **Exception B:** `docs/FREEZE_ALLOWLIST.md` — today **exactly one entry: the E6 patch** (F1/F2 fixes + stage‑2 runtime fetch, decided 2026‑10‑19) | the allowlist is a committed file reviewed like any other; `check_freeze.py` fails on any `src/` diff not covered by it, and the entry must be retired once E6 merges so the freeze returns to strict |
| Everything else outside `src/` | free to add/change: `.github/`, `api/`, `data/`, `public/data/`, `scripts/`, `tests/`, `docs/`, root configs |

This distinction matters: the app reads its catalog from `SEED_DATA` **at build time**, and with `src/` frozen there is no runtime‑fetch hook to add. Therefore:

- **Data freshness arrives only via rebuild.** Publish path (a) from §11.6 is not a preference here, it is the *only* path: bot commits the new JSON → `regenerate_seeds.py` rewrites `SEED_DATA` → push → Vercel rebuild (~1–2 min) → live data. (Path (b)/(c) needs `src/lib/api.ts` → unfreeze, §14.6.)
- **The `/api/*` routes still ship.** They live in `/api` at the repo root (Vercel deploys them independently of the SPA), and they serve `/api/health`, exports, OG images and the manifest to anyone — ops tooling, monitors, future clients. The SPA simply doesn't call them yet.
- **`public/data/*` is copied into `dist/` automatically by Vite**, so publishing the JSON is a file copy — no extra CDN, no extra config, and it does **not** enter the JS bundle.

### 14.2 Target layout — every path, its role and its state

```
OPP-Track/                       ← repo root = Vercel project root (framework: vite, output: dist)
├── .github/workflows/           ✚ NEW — the engine (§11.6, E5)
│   ├── verify.yml               push/PR: freeze check + typecheck + test + build + node validate + py validate (3–6 min)
│   ├── scrape-quick.yml         workflow_dispatch only: --multi --validate → publish (10–20 min, manual spot runs)
│   └── scrape-full.yml          cron 0 */8 * * * (00:00/08:00/16:00 UTC): --multi --detailed --enrich → publish (60–90 min)
├── api/                         ✚ NEW — 9 read‑only functions (§11.4, E4) + shared lib
│   ├── _lib/
│   │   ├── loadDataset.ts       reads data/scraped_opportunities.json once per cold start, caches in memory
│   │   ├── respond.ts           `{error, code}` shape, CORS, JSON headers
│   │   └── validate.ts          query‑param clamping (mirror of the data validator's rules)
│   ├── health.ts  manifest.ts  opportunities.ts  stats.ts  sources.ts  og.ts  export.ts
│   └── opportunities/[id].ts
├── data/                        the only data store (§11.2, E1)
│   ├── scraped_opportunities.json  ⚠️ TRACKED (un‑ignore; canonical, 2,588 items, ~1.9 MB)
│   ├── manifest.json            ✚ NEW tracked — counts + histograms + sha256 + provenance
│   ├── scraper_health.json      tracked (feeds /api/sources)
│   ├── reports/publish-*.md     ✚ NEW tracked — validation result + diff per run (audit trail)
│   └── backups/                 ✚ NEW ignored — rotation: 7 daily + 8 weekly (atomic writes)
├── public/
│   ├── favicon.svg              keep
│   └── data/                    ✚ NEW generated — published manifest + opportunities.<sha8>.json (immutable)
├── scripts/
│   ├── scrapers/                84 built‑ins + run_all.py + enrich.py + health_check.py + sources.json
│   │   └── (retire) test_*.py, _check.py, _run_new.py → scripts/dev/ (B19)
│   ├── publish_dataset.py       ✚ NEW — validate → sanity gate → manifest+sha256 → atomic write →
│   │                            backup rotate → regenerate_seeds.py → public/data copy → report
│   ├── sanity_gate.py           ✚ NEW — ±20 % count, ±50 % per‑source, enum check, link validity
│   ├── check_freeze.py          ✚ NEW — enforces the `src/` freeze (§14.1)
│   ├── rotate_backups.py        ✚ NEW — 7 daily / 8 weekly retention
│   ├── regenerate_seeds.py      keep — sole writer of src/lib/storage.ts
│   ├── merge_seeds.py           retire (B8) — emits the pre‑v4 format that breaks TS2590
│   ├── check_all_links.py  validation_report.py  validate_live.py   keep, but de‑hardcode (B10)
│   └── validate-data.mjs        keep — fix the 3 stale rules (B2); becomes the publish gate
├── tests/
│   ├── migration.test.mjs       keep (23 tests, esbuild‑bundled real module)
│   └── test_sanity_gate.py      ✚ NEW — pytest over gate + manifest + publish idempotence
├── docs/                        14 files, most describe a system that no longer exists (B21/B22)
│   ├── ARCHITECTURE.md  SCRAPING_WORKFLOW.md  SCRAPING_SYSTEM.md   rewrite to match reality
│   ├── ENGINE.md         ✚ NEW — runbooks: local run, publish, restore drill, alert response
│   ├── DATA_CONTRACT.md  ✚ NEW — §11.2 contract, enum + evergreen rules, checksum policy
│   └── (retire or fold into the above) RESEARCH_LOG, RESEARCH_WORKFLOW, act-this-week,
│       research-hackathons-2026, RISKS_AND_EDGE_CASES, TASKS, PRD, PROJECT_OVERVIEW,
│       KNOWN_ISSUES_AND_DECISIONS, CODING_RULES
├── frontend/PLAN.md             user's own plan — **needs rewriting**: it is built around Supabase,
│                                accounts and a `profiles`/`opportunities` schema, all withdrawn
├── .nvmrc                       ✚ NEW — 22 (Vercel must build with the pinned version, B22)
├── requirements.txt             ✚ NEW — pinned direct Python deps (B4)
├── .gitattributes               ✚ NEW — `data/scraped_opportunities.json linguist-generated=true`
├── vercel.json                  exists — extend with cache headers for /data/* and /api/*
├── package.json / tsconfig.json / vite.config.ts / index.html   keep (uncommitted v4 work, B1)
│                            add `engines.node`, add scripts: publish:data, check:freeze, verify:all
├── src/                         ❄️ FROZEN — read the freeze rule in §14.1
├── dist/                        build output (gitignored)
└── (delete at cleanup) npm_anim.log, run2_stream.log, validation_err.txt,
                         validation_report.txt — stray run artifacts at the repo root
```

### 14.3 Ownership — one writer per file

| File | Sole writer | Readers | Invariant enforced by |
|---|---|---|---|
| `data/scraped_opportunities.json` | `run_all.py` (pipeline) | `publish_dataset.py`, `regenerate_seeds.py`, `api/_lib/loadDataset.ts` | Python schema validation + sanity gate |
| `data/manifest.json` | `publish_dataset.py` | `verify.yml`, `/api/health`, the SPA | `sha256` recomputed at publish **and** at read |
| `src/lib/storage.ts` | `regenerate_seeds.py` only | Vite build, `tests/migration.test.mjs` | freeze check + typecheck + 23 tests |
| `public/data/*` | `publish_dataset.py` | browser, monitors | byte‑identity + `sha256` vs manifest |
| `data/reports/*` | `publish_dataset.py` | humans, `/api/report/latest` | append‑only, one per publish |
| `data/backups/*` | `rotate_backups.py` | restore drill | atomic write + retention count |
| `.github/workflows/*` | humans | Actions | pinned third‑party actions by SHA |
| everything else | humans / agents | — | `verify.yml` |

The point of this table is that **no file has two writers** — the class of bug where a refresh overwrites a fix (B6/B7/B8) becomes structurally impossible rather than merely unlikely.

### 14.4 How a data refresh actually flows, end to end

```
cron (Actions) → run_all.py ──writes──▶ data/scraped_opportunities.json   (atomic)
                    │
                    ├─ validate (python, fail = stop)
                    ├─ sanity_gate.py vs previous manifest (fail = stop + Issue)
                    └─ publish_dataset.py
                         ├─ regenerate_seeds.py ──writes──▶ src/lib/storage.ts (SEED_DATA, version bump)
                         ├─ writes data/manifest.json (sha256, counts, provenance)
                         ├─ copies to public/data/opportunities.<sha8>.json + manifest.json
                         ├─ writes data/reports/publish-YYYYMMDD.md
                         └─ rotate_backups.py → data/backups/
                    │
                    ▼
        git push (single writer, rebase-retry)
                    │  └─ verify.yml: freeze check + typecheck + test + build + validate
                    ▼
        Vercel rebuild (~1–2 min) → dist/ (SPA + /api functions + public/data asset)
                    │
                    ▼
        Actions GET /api/health → assert age < 24 h and sha8 matches  → done
```

One command locally reproduces the whole right‑hand side: `npm run publish:data`.

### 14.5 File‑touch plan per milestone (mechanical; `src/` touched only at E6, allowlisted)

| Milestone | Creates | Modifies | Retires/deletes |
|---|---|---|---|
| **E1** protect the data | `data/manifest.json`, `data/backups/`, `scripts/rotate_backups.py`, `.gitattributes`, `docs/DATA_CONTRACT.md` | `.gitignore` (un‑ignore the canonical JSON, ignore `data/backups/`, `*.log`, `validation_*.txt`) | — |
| **E2** publish gate | `scripts/sanity_gate.py`, `tests/test_sanity_gate.py` | `scripts/validate-data.mjs` (3 rules), `package.json` (`verify:all`, `check:freeze`, `publish:data`) | — |
| **E3** publish pipeline | `scripts/publish_dataset.py`, `data/reports/` | `scripts/regenerate_seeds.py` (idempotent, stable‑id mode for B6) | `scripts/merge_seeds.py` (B8) |
| **E4** read API | `api/_lib/*.ts`, `api/*.ts`, `api/opportunities/[id].ts` | `vercel.json` (cache headers), `package.json` (`engines`) | — |
| **E5** the engine | `.github/workflows/verify.yml`, `scrape-quick.yml`, `scrape-full.yml`, `requirements.txt`, `.nvmrc` | `scripts/scrapers/*.py` (atomic writes, relative paths B10, no fabricated links B11) | `scripts/scrapers/test_*.py`, `_check.py`, `_run_new.py` → `scripts/dev/` |
| **E6** controlled unfreeze #1 | `docs/FREEZE_ALLOWLIST.md` | **the single allowlisted `src/` patch:** F1/F2 fixes (`date`/`validation` guard) + stage‑2 runtime fetch (`src/lib/api.ts`, manifest‑first loader, IndexedDB cache) | — |
| **E7** production deploy | `docs/ENGINE.md` | `README.md` (real quickstart), `docs/ARCHITECTURE.md`, `docs/SCRAPING_WORKFLOW.md` | root stray logs/`validation_*.txt` |
| **E8** watchdog & retention | freshness job (`age < 12 h`), tag/Release + **monthly squash** step in `scrape-full.yml` | — | `frontend/PLAN.md` rewrite (accounts/Supabase removed) |

### 14.6 Frozen‑`src/` impact register — what we cannot fix, and the honest substitute

| F‑finding | Visible consequence on the live site | Substitute while `src/` is frozen | Unfreeze needed? |
|---|---|---|---|
| **F1** evergreen deadline | **1,718 of 2,588 cards read "NaN days left"**; editing one is blocked by the form | **none** — an empty deadline can't be patched from data without fabricating dates, and dropping evergreen items would break the completeness rule (§11.2) | **Yes — decided: fixed at E6**, the single allowlisted patch (before the E7 public deploy) |
| **F2** reminder storm | fires only if the visitor enables notifications | the same one‑line guard fix sits in the same patch | Yes — **E6**, with F1 (decided) |
| **F3** migration drift / positional ids | statuses attach to the wrong row after a renumbering | **fixed at the generator level**: `regenerate_seeds.py` emits **fingerprint‑hash ids** (B6/B24) — data‑side change, no `src/` touch | No |
| **F4** no virtualization (1,940 cards) | slow first interaction | none; page‑size clamping at the API doesn't help a bundled catalog | Yes (later, with the virtualised list) |
| **F5/F6** re‑parse + quota | lag on every status change | none | Yes |
| **F8** no ErrorBoundary | an unknown `type` from a scraper **white‑screens the app** | **substituted by the publish gate**: `sanity_gate.py` rejects any item whose `type` is not in the enum before it can reach the bundle | No (for the crash cause); Yes (for the resilience) |
| **F7** 1,093‑option tag select | unusable filter | none | Yes |
| **F9/F16/F20** theme/dead code/design system | visual polish | none | Yes (with the shadcn cleanup) |
| **F10/F11** router, OG/SEO | no deep links, no share previews | `/api/og` + `/api/opportunities/:id` are built in §11.4 **now**, so the URLs exist the day `src/` is unfrozen | Yes |

Net: **E1–E5 and E7–E8 ship with `src/` strictly frozen**, and the E6 patch (decided 2026‑10‑19 — see §14.8 item 3) removes the only visible defect class before the E7 public deploy while also adding the runtime fetch. Everything else stays parked with a named gate, so the freeze's cost is a written list rather than a vague backlog.

### 14.7 Efficiency notes — why this layout is the efficient one

- **One command replaces five manual steps** (`npm run publish:data` = validate → gate → manifest → backup → seeds → public asset → report).
- **Vite already does the heavy lifting**: `public/` is copied into `dist/`, so publishing data costs a file copy, not a new pipeline.
- **Caching**: pip + npm + `~/.cache/ms-playwright` turns a ~6 min runner setup into ~2 min; on 30 runs/month that is ~2 h of Actions minutes saved.
- **Bundle stays honest**: the published JSON is a *static asset*, not part of the JS — the 1.56 MB bundle is unchanged by publishing, and shrinks only when `src/` is unfrozen and `SEED_DATA` becomes a fallback rather than the source.
- **No duplicate data stores**: JSON → manifest → SEED_DATA → public asset are four views of one write, produced by one command, verified by one `sha256`.
- **Repo growth is capped by design**: only the canonical JSON + manifest + reports are tracked; weekly tags and monthly Release archives hold the history.

### 14.8 Four blocking decisions (settled 2026‑10‑19)

| # | Question | **Decision** | Consequence / carry‑over |
|---|---|---|---|
| 1 | Freshness model under the `src/` freeze | **Both, staged** — rebuild‑on‑commit for E1–E5, then the runtime fetch as part of the E6 unfreeze | No rebuild needed for data after E6; publishing path (a) only until then (§11.6) |
| 2 | Schedule | **Full pipeline every 8 h** — `0 */8 * * *` (00:00/08:00/16:00 UTC) | ⚠️ **Open sub‑item:** repo is **private** → ~6,800 Actions min/month vs 2,000 free. Make the repo public at deploy (recommended), pay, or degrade to every‑8‑h quick + weekly full — §11.6 budget box |
| 3 | The visible defect (F1/F2) & the freeze's exception | **Unfreeze a minimal F1/F2 patch first** — milestone **E6**, before the E7 public deploy; generator‑written `src/lib/storage.ts` accepted as Exception A | One allowlist entry (`docs/FREEZE_ALLOWLIST.md`), retired after E6 merges; F‑1/F‑2 (§12.5) become deploy gates |
| 4 | Data protection posture | **Track the canonical JSON in git + monthly squash** | git history = restore path; weekly tags + monthly Release archive; monthly squash keeps the 1.9 MB/refresh history bounded |

---

## 15. Appendix

### A. Backend file inventory

| Path | Role |
|---|---|
| `scripts/scrapers/base.py` | Schema, deadline parsing, dedup, stale filter, quality scoring |
| `scripts/scrapers/run_all.py` | Orchestrator (84 built‑ins, `--multi`, `--detailed`, `--validate`, `--enrich`, `--quality`) |
| `scripts/scrapers/multi_source.py` | Selector‑driven scraper from `sources.json` (scrapling/httpx/api) |
| `scripts/scrapers/enrich.py` | Detail‑page enrichment (5 platforms) |
| `scripts/scrapers/sources.json` | Source registry (60 entries, 55 overlap built‑ins) |
| `scripts/scrapers/health_check.py` | Parallel smoke test of all scrapers (hardcoded Windows paths — B10) |
| `scripts/scrapers/test_*.py`, `_check.py`, `_run_new.py` | Ad‑hoc dev scripts (B19) |
| `scripts/regenerate_seeds.py` | Full `SEED_DATA` regeneration + version bump |
| `scripts/merge_seeds.py` | Legacy incremental merge (stale format — B8) |
| `scripts/validate-data.mjs` | Seed validator (stale rules — B2) |
| `scripts/check_all_links.py`, `scripts/validate_live.py`, `scripts/validation_report.py` | Link/freshness audits (hardcoded date — B10) |
| `src/lib/storage.ts` | Seed data + localStorage load/save + versioned migration |
| `tests/migration.test.mjs` | 23 migration tests via esbuild import |
| `data/*` | Generated artifacts (mostly ignored; 4 tracked — B9) |

### B. Evidence (audit date 2026‑10‑19)

- `npm run validate`: `entries: 2577` · `by type: {"Hackathon":430,"Competition":670,"Internship":664,"Certification":813}` · `errors: 3968, warnings: 637`
- Python validator: `Validated 2577 items, 0 errors`
- `npm test`: `ALL 23 TESTS PASSED` · typecheck exit 0 · build exit 0 (1,559.58 kB JS / 226.16 kB gzip)
- `npm ls eslint` → empty; `npm ls autoprefixer postcss` → postcss only, as a Vite transitive dep
- Tracked generated artifacts: `data/pipeline_results.json`, `data/scraper_health.json`, 2× `data/scraped_opportunities_backup_20260912_*.json`
- No secrets found in `scripts/**` (grep for api_key/secret/token/password/bearer/authorization)

### C. Command reference (current)

| Purpose | Command |
|---|---|
| Full scrape | `python scripts/scrapers/run_all.py --multi --detailed` |
| Quick scrape | `python scripts/scrapers/run_all.py --quick` |
| Schema validate (Python) | `python scripts/scrapers/run_all.py --validate` |
| Regenerate seeds | `python scripts/regenerate_seeds.py` (`--dry-run` to preview) |
| Validate seeds (Node) | `npm run validate` · `npm run validate:links` |
| Health check | `python -m scripts.scrapers.multi_source --list` |
| App checks | `npm run typecheck` · `npm test` · `npm run build` |
