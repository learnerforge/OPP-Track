# API Reference (read-only)

Nine GET-only serverless functions under `api/` (§11.4 of `fullstack.md`). No auth, no write endpoints — `POST`/`PATCH`/`DELETE` return **405** `{error, code:'method_not_allowed'}`. All errors use the envelope `{"error": "<human message>", "code": "<machine code>"}`. Codes: `invalid_param` (400), `not_found` (404), `method_not_allowed` (405), `dataset_unavailable` (503), `internal_error` (500).

Query params are validated and clamped server-side with the data validator's rules (`page_size` 1–100, `type` enum, dates `YYYY-MM-DD`). Unknown params are ignored. Nothing under `src/` consumes these yet — the SPA uses the bundled snapshot until the E6 unfreeze; the runtime fetch (manifest-first ladder, §11.5) arrives then.

## Routes

| Route | Purpose | Cache-Control |
|---|---|---|
| `GET /api/health` | freshness smoke: `{ok, item_count, sha256, published_sha8, generated_at, age_hours, fresh}` (`fresh` = `age_hours < 12`) | `no-store` |
| `GET /api/manifest` | manifest (CORS-enabled `*`); reads `data/manifest.json`, else derives `{sha256, sha8, item_count, generated_at, origin:'derived'}` from the canonical file | `public, s-maxage=300, stale-while-revalidate=86400` |
| `GET /api/opportunities` | filtered + paginated list → `{items, page, page_size, total, total_pages}` | `public, s-maxage=3600, stale-while-revalidate=86400` |
| `GET /api/opportunities/:id` | single record by stable fingerprint id; 404 `{error, code:'not_found'}` otherwise | `public, s-maxage=3600` |
| `GET /api/stats` | `{total, by_type, by_source, rolling, dated, closing_soon_7d}` | `public, s-maxage=3600, stale-while-revalidate=86400` |
| `GET /api/sources` | `{sources: [{source, item_count}], health}` — health map from `data/scraper_health.json`, `null` if absent | `public, s-maxage=3600, stale-while-revalidate=86400` |
| `GET /api/report/latest` | newest `data/reports/publish-*.md` → `{filename, generated_at, body}`; 404 if none | `public, s-maxage=300` |
| `GET /api/og` | dynamic OG image (SVG) → `image/svg+xml` | `public, s-maxage=86400` |
| `GET /api/export` | filtered set as `csv`, `ics` or `json` (attachment download) | `public, s-maxage=3600, stale-while-revalidate=86400` |

## Shared list params (`/api/opportunities`, `/api/export`)

| Param | Values | Default |
|---|---|---|
| `q` | free text, ≤ 200 chars (matches title, source, eligibility, tags) | — |
| `type` | `Hackathon` \| `Internship` \| `Certification` \| `Competition` | — |
| `source` | case-insensitive exact source name | — |
| `tag` | case-insensitive exact tag | — |
| `status` | `rolling` — only empty-deadline (evergreen) items | — |
| `deadline_within` | days `1–365` — dated items due within N days (not past) | — |
| `sort` | `deadline_asc` \| `deadline_desc` \| `relevance` (rolling always last) | `deadline_asc` |
| `page` | integer ≥ 1 | `1` |
| `page_size` | integer `1–100` (out-of-range → 400, not clamped) | `50` |

Example — `GET /api/opportunities?status=rolling&type=Hackathon&page_size=2`:

```json
{
  "items": [{ "title": "…", "type": "Hackathon", "deadline": "", "fingerprint": "ba5fd2ae33ae", "…": "…" }],
  "page": 1, "page_size": 2, "total": 311, "total_pages": 156
}
```

## Export specifics

- `format=json` (default): `{items, total, …}` — the **complete** filtered set, not paginated (completeness rule §11.2).
- `format=csv`: manual RFC-4180-style quoting, columns `id,title,type,source,link,deadline,eligibility,tags,location,date_added` (tags `; `-joined), CRLF rows.
- `format=ics`: RFC 5545 `VCALENDAR` of **dated** items only (`DTSTART;VALUE=DATE`). Rolling items have no calendar date, so they are excluded and counted in the calendar's `X-WR-CALDESC` note.

## Limitations & notes

- **`/api/og` returns SVG.** Facebook/LinkedIn/Twitter crawlers generally do **not** render SVG OG images (PNG required). The URL and route exist now (F11); a PNG renderer can replace the internals later without a route change.
- HEAD is treated as a read-only alias of GET; every other method 405s.
- Static assets (not functions): `GET /data/manifest.json` (`s-maxage=300, swr=86400`) and `GET /data/opportunities.<sha8>.json` (`max-age=31536000, immutable`) — headers set in `vercel.json`.
- Dataset is loaded once per cold start into module scope; `data/manifest.json` absence degrades to an on-the-fly sha256/count derived from `data/scraped_opportunities.json`.
- Rate limiting (429) is delegated to Vercel WAF, not application code.

Local typecheck: `npx tsc -p api/tsconfig.json --noEmit`. Handlers are plain `(req, res)` functions and can be smoke-tested directly under Node ≥ 22.18 (native type stripping).
