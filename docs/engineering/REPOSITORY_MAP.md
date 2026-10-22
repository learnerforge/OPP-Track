# Repository map

## Deployed path

`vercel.json` deploys the Vite application rooted at `app/` and the Vercel
functions in `api/`. The deployed application reads the published static
catalog from `public/data/` and falls back to `/api/opportunities`.

```
scrapers -> data/scraped_opportunities.json -> publish_dataset.py
         -> data/manifest.json + public/data/* -> app/ and api/
```

## Important directories

| Path | Purpose | Status |
|---|---|---|
| `app/` | Deployed React/Vite application (`/`, `/login`, `/events`) | Current deployment target |
| `api/` | Vercel read/export/health/edit functions | Current deployment target |
| `data/` | Canonical scraped catalog, manifest, health, publish reports | Pipeline source of truth |
| `public/data/` | Static published catalog and manifest | Deployment artifact |
| `scripts/` | Data validation, publication, backup, and scraper pipeline | Operational code |
| `tests/` | Legacy storage migration and Python sanity-gate tests | Does not cover deployed UI/API |
| `src/` | Earlier React/local-storage application | Legacy; frozen by policy |
| `frontend/` | Another earlier frontend copy | Legacy/unconfirmed |

## Current architectural risks

- The root scripts and CI primarily test `src/`, not `app/` or `api/`.
- The three frontend trees have divergent product assumptions.
- The edit feature currently relies on browser-visible shared-secret auth and
  must not be treated as access-controlled until replaced with server-side auth.

