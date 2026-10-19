# OPP-Track

A personal opportunity discovery and tracking dashboard for students. OppTrack automatically scrapes hackathons, internships, competitions, and certifications from 70+ platforms into a single JSON catalog, then lets you track your own progress on top of it — deadline sorting, urgency color-coding, countdown timers, status tracking, and browser reminders so nothing is ever missed.

**Current catalog: 2,588 opportunities from 73 sources** (440 hackathons, 712 competitions, 642 internships, 794 certifications; 1,672 evergreen/rolling + 916 with hard deadlines).

## Tech Stack

- **React 19** + **TypeScript** (strict), bundled with **Vite 6**
- **Tailwind CSS v4** + **shadcn/ui** components
- **No database** — JSON files are the single source of truth; the app is a self-contained SPA on Vercel
- **Scheduled data engine** — GitHub Actions re-scrapes every 8 hours and publishes a fresh catalog
- **Read-only API** — Vercel serverless functions serve the full dataset as JSON/CSV/ICS

## Features

- **Automatic catalog** — 2,588 seeded opportunities from 8 scrapers (Devpost, Devfolio, Unstop, HackerEarth, Internshala, and more), refreshed by the engine
- **Personal tracking layered on top** — status (Not Started → Applied → In Progress → Rejected/Completed), notes, manual add/edit/delete
- **Deadline dashboard** — urgency color-coding (🔴 ≤2d, 🟡 3–7d, 🟢 8+d, ⚪ rolling/completed), countdowns, weekly review of closing-soon items
- **Filters & search** — type, status, source, tag, title text; evergreen ("rolling") items handled as first-class
- **Reminders** — browser notifications for upcoming deadlines
- **Stats panel** — counts by status, type, and monthly progress
- **Export** — JSON/CSV download; the API also serves iCalendar (ICS)
- **Complete data, always** — every copy of the catalog is the full set; never truncated or sampled

## Quick Start

```bash
npm install
npm run dev        # http://localhost:5173
```

```bash
npm run build      # production build → dist/
npm run preview    # serve the build locally
```

Node is pinned to **22.22.3** (`.nvmrc`; `engines` enforces ≥22 <23).

## Data Pipeline

The catalog lives in `data/scraped_opportunities.json` (canonical, committed). A scheduled engine refreshes it and the app redeploys — you never edit it by hand:

```bash
npm run scrape              # run all scrapers (writes the canonical JSON)
npm run scrape:quick        # fast subset
npm run validate            # schema/contract validation (exit 1 on errors)
npm run validate:links      # additionally HTTP-checks every link (network)
npm run publish:data        # guarded publish: validate → sanity gate →
                            #   manifest+sha256 → public/data copy →
                            #   seed regeneration → backup rotation → report
npm run verify:all          # typecheck + tests + validate (CI gate)
python scripts/check_freeze.py   # src/ freeze enforcement (see below)
```

**Freshness:** `.github/workflows/scrape-full.yml` runs every 8 hours (00:00/08:00/16:00 UTC), scrapes all sources, runs the publish pipeline, commits the new dataset + regenerated seed bundle, and Vercel rebuilds. `scrape-quick.yml` is manual-only. `verify.yml` gates every push/PR (freeze check, typecheck, 23 migration tests, dataset validation, sanity gate).

**Integrity:** every publish records `sha256`, counts, and provenance in `data/manifest.json`, copies the byte-identical dataset to `public/data/opportunities.<sha8>.json` (immutable), and rotates backups into `data/backups/` (7 daily + 8 weekly). The sanity gate refuses to publish a dataset that collapsed >20% or lost >50% of any source.

## Read-Only API

Deployed as Vercel functions under `/api` (GET only, no writes):

| Route | Serves |
|---|---|
| `/api/health` | dataset freshness: item count, sha256, age |
| `/api/manifest` | current manifest (counts, provenance) |
| `/api/opportunities` | filtered + paginated catalog (`q`, `type`, `source`, `tag`, `status=rolling`, `deadline_within`, `sort`, `page`, `page_size`) |
| `/api/opportunities/:id` | single record |
| `/api/stats` | type/source histograms, closing-soon count |
| `/api/sources` | source registry + scraper health |
| `/api/report/latest` | latest publish report |
| `/api/og` | dynamic Open-Graph image |
| `/api/export` | full export as `csv` / `ics` / `json` |

See `docs/API.md` for parameters, cache policies, and error shapes.

## Project Structure

```
OPP-Track/
├── api/                        # Vercel serverless functions (read-only)
│   ├── _lib/                   #   shared loadDataset / respond / validate / types
│   └── *.ts                    #   health, manifest, opportunities, stats, sources,
│                               #   report/latest, og, export
├── data/
│   ├── scraped_opportunities.json  # CANONICAL dataset (2,588 items, 73 sources)
│   ├── manifest.json               # sha256 + counts + provenance (publish-written)
│   ├── scraper_health.json         # per-source health map
│   ├── reports/                    # one publish report per run
│   └── backups/                    # rotation: 7 daily + 8 weekly (gitignored)
├── public/data/                # published immutable copies + manifest
├── .github/workflows/          # verify.yml, scrape-full.yml (0 */8 * * *), scrape-quick.yml
├── scripts/
│   ├── scrapers/               # 8 source scrapers + orchestrator (run_all.py)
│   ├── publish_dataset.py      # the guarded publish command
│   ├── sanity_gate.py          # regression gate (±20% total, ±50% per source)
│   ├── rotate_backups.py       # backup rotation
│   ├── regenerate_seeds.py     # sole writer of src/lib/storage.ts
│   ├── check_freeze.py         # src/ freeze enforcement
│   └── validate-data.mjs       # dataset contract validator
├── src/                        # React app (FROZEN — see freeze policy)
│   ├── components/ (+ ui/)     #   app + shadcn/ui components
│   ├── hooks/ lib/ utils/      #   state, storage, helpers
│   ├── types/ constants/       #   data model + options
│   └── lib/storage.ts          #   GENERATED seed bundle — never edit by hand
├── tests/                      # migration.test.mjs (npm test) + sanity-gate tests
├── docs/                       # ARCHITECTURE, API, DATA_CONTRACT, ENGINE, …
└── fullstack.md                # master build/deploy plan
```

## Data Contract (summary)

- Types: `Hackathon | Internship | Certification | Competition`
- `deadline: ""` means **rolling/evergreen** — dates are never fabricated
- `link` is a valid `http(s)` URL or empty — never fabricated
- Every file has exactly **one writer** (see `docs/DATA_CONTRACT.md`)
- `src/lib/storage.ts` is generated from the canonical dataset by `scripts/regenerate_seeds.py` — the only code allowed to write into `src/`

**Freeze policy:** `src/` is frozen; the only exception is the generator-written `src/lib/storage.ts`. `scripts/check_freeze.py` enforces this in CI (`docs/FREEZE_ALLOWLIST.md` lists deliberate exceptions).

## Documentation

| Doc | Contents |
|---|---|
| `fullstack.md` | master build/deploy plan (milestones, backlog, decisions) |
| `docs/ARCHITECTURE.md` | system map: engine → data → SPA |
| `docs/DATA_CONTRACT.md` | file inventory, field contracts, one-writer table |
| `docs/API.md` | API routes, parameters, cache policies |
| `docs/ENGINE.md` | scheduled-refresh runbook (ops: runs, restore, alerts) |
| `docs/FREEZE_ALLOWLIST.md` | freeze policy + exceptions |

## License

MIT
