# OPP-Track Scraping System — Definitive Reference

> Version 1.0 | Last updated: August 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Quick Start](#2-quick-start)
3. [Scraper Reference](#3-scraper-reference)
4. [Multi-Source Framework](#4-multi-source-framework)
5. [Enrichment Pipeline](#5-enrichment-pipeline)
6. [Data Schema](#6-data-schema)
7. [Pipeline Commands](#7-pipeline-commands)
8. [Quality System](#8-quality-system)
9. [Staleness Detection](#9-staleness-detection)
10. [Source Directory](#10-source-directory)
11. [Troubleshooting](#11-troubleshooting)
12. [Future Roadmap](#12-future-roadmap)

---

## 1. System Overview

### What It Does

OPP-Track's scraping system automatically discovers hackathons, internships, and certifications from 50+ platforms worldwide. It normalizes heterogeneous web data into a unified JSON schema, deduplicates across sources, enriches missing fields by visiting detail pages, and scores quality on a 0–100 scale — feeding clean data into the React UI.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES (50+)                          │
│  Devfolio │ Devpost │ Unstop │ HackerEarth │ Internshala │ ...     │
│  MLH │ Kaggle │ Codeforces │ LinkedIn │ Google Careers │ ...       │
└────────────┬──────────────────────────────────┬─────────────────────┘
             │                                  │
             ▼                                  ▼
┌────────────────────────┐    ┌──────────────────────────────────┐
│   5 BUILT-IN SCRAPERS  │    │   MULTI-SOURCE FRAMEWORK         │
│   (dedicated .py)      │    │   (sources.json + dispatch)      │
│                        │    │                                  │
│   devfolio.py          │    │   multi_source.py                │
│   devpost.py           │    │   ├─ _scrape_scrapling()         │
│   unstop.py            │    │   ├─ _scrape_httpx()             │
│   hackerearth.py       │    │   └─ _scrape_api()               │
│   internshala.py       │    │                                  │
└────────────┬───────────┘    └───────────────┬──────────────────┘
             │                                │
             └────────────┬───────────────────┘
                          ▼
            ┌─────────────────────────┐
            │      run_all.py         │
            │   (Pipeline Orchestrator)│
            │                         │
            │  1. Scrape all sources  │
            │  2. Deduplicate         │
            │  3. Quality score       │
            │  4. Classify locations  │
            │  5. Enrich (optional)   │
            │  6. Validate            │
            │  7. Save                │
            └────────────┬────────────┘
                         ▼
            ┌─────────────────────────┐
            │  scraped_opportunities  │
            │        .json            │  ◄── Raw scraped data
            └────────────┬────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
┌──────────────────┐        ┌──────────────────────┐
│   enrich.py      │        │   merge_seeds.py     │
│ (Tier-2 Detail)  │        │ (JSON → TS entries)  │
│                  │        │                      │
│ Visits detail    │        │ Deduplicates vs      │
│ pages to fill    │        │ existing SEED_DATA   │
│ missing fields   │        │ Generates new entries│
└──────────────────┘        └──────────┬───────────┘
                                       ▼
                          ┌──────────────────────┐
                          │   storage.ts         │
                          │   (SEED_DATA)        │ ◄── Manual merge
                          │   SEED_VERSION = 8   │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │   React UI           │
                          │   Dashboard / Cards  │
                          └──────────────────────┘
```

### Data Flow

1. **Scrape** — Each scraper fetches a platform's listing page via Scrapling's `StealthyFetcher` (headless Chromium) or `httpx` (static HTML), extracts opportunity cards using CSS selectors, and returns `ScrapeItem` objects.
2. **Deduplicate** — Items are fingerprinted by `SHA-256(title + source + type)[:12]`. Duplicates across sources are removed (first occurrence wins).
3. **Quality Score** — Each item is scored 0–100 based on field completeness. Locations are auto-classified as Online/Hybrid/Offline using regex heuristics.
4. **Enrich** — Items scoring below 50 have their detail pages visited. Platform-specific extractors pull deadlines, prizes, eligibility, and participants from the full page HTML.
5. **Validate** — Items are checked for required fields, valid types, proper date formats, and URL schemes. Invalid items are logged and excluded.
6. **Save** — Valid items are written to `data/scraped_opportunities.json`.
7. **Merge** — `merge_seeds.py` reads the JSON, deduplicates against existing `SEED_DATA` in `storage.ts`, and generates TypeScript entries for manual review and merge.

---

## 2. Quick Start

### Prerequisites

```bash
# Python 3.13+ required
python --version   # 3.13+

# Install scraping dependencies
pip install "scrapling[fetchers]" httpx

# Install headless Chromium (required by StealthyFetcher)
patchright install chromium
```

### First Run

```bash
# Run the full pipeline (all 5 built-in scrapers)
npm run scrape

# Or run directly
python scripts/scrapers/run_all.py
```

This will:
1. Scrape Devfolio, Devpost, Unstop, HackerEarth, Internshala
2. Deduplicate results
3. Score quality and classify locations
4. Validate and save to `data/scraped_opportunities.json`

### How to Add a New Source

**Option A — Quick (sources.json):**

1. Open `scripts/scrapers/sources.json`
2. Add a new entry to the `sources` array (see [Section 4](#4-multi-source-framework))
3. Run `npm run scrape:multi`

**Option B — Full scraper (dedicated .py):**

1. Create `scripts/scrapers/myplatform.py`
2. Implement a `scrape_myplatform()` function returning `list[ScrapeItem]`
3. Register it in `run_all.py`'s `SCRAPERS` dict
4. Run `npm run scrape`

---

## 3. Scraper Reference

### 3.1 Devfolio (`devfolio.py`)

**What it scrapes:** Open and upcoming hackathons from [devfolio.co](https://devfolio.co/hackathons/open)

**Technique:** StealthyFetcher (headless Chromium). Devfolio is a Next.js SPA that requires JavaScript rendering.

**CSS Selectors Used:**

| Field | Selector | Notes |
|-------|----------|-------|
| Card links | `a[class*="Link__LinkBase"]` | Filters to `.devfolio.co` hrefs only |
| Title | `h3::text` inside card | Filtered against `SKIP_TITLES` set |
| Start date | Regex: `Starts \d{1,2}/\d{1,2}/\d{2,4}` | Position-matched to card order |
| Participants | Regex: `\+\d+\s*participat` | Position-matched to card order |

**Date Parsing:** Custom `_parse_devfolio_date()` handles `Starts 27/08/26` → `2026-08-27`

**Known Limitations:**
- Relies on positional matching (dates/participants matched by index to cards — can misalign if elements are reordered)
- Location (Online/Offline) not reliably extracted from listing page
- No prize pool data on listing page
- Infinite scroll not handled — only initial page content captured

**Test independently:**
```bash
python scripts/scrapers/devfolio.py
```

---

### 3.2 Devpost (`devpost.py`)

**What it scrapes:** Upcoming and open hackathons from [devpost.com](https://devpost.com/hackathons)

**Technique:** StealthyFetcher. Devpost is a Rails app with server-rendered HTML, but StealthyFetcher is used for reliability.

**CSS Selectors Used:**

| Field | Selector | Notes |
|-------|----------|-------|
| Card container | `.hackathon-tile` | Main card wrapper |
| Title | `h3` | First h3 inside tile |
| Link | `a.tile-anchor[href]` | Prepends `https://devpost.com` if relative |
| Date range | `.submission-period` | Parsed to end date of range |
| Tags | `.theme-label` | Reads `title` attribute |
| Location | `.info-with-icon span` | Checks for Online/Offline/Hybrid/In Person |
| Host | `.host-label` or `.host` | Reads `title` attribute |
| Prize | `.prize-amount` | Extracts nested text via regex strip |
| Participants | `.participants strong` | Number in strong tag |
| Status | `.hackathon-status` | e.g. "Open", "Upcoming" |

**Date Parsing:** `_parse_date_range()` extracts end date from ranges like `Aug 29 - Sep 01, 2026`

**Known Limitations:**
- Only captures server-rendered first page (no infinite scroll)
- Some hackathons require login to see full details
- Prize amounts sometimes include non-numeric characters

**Test independently:**
```bash
python scripts/scrapers/devpost.py
```

---

### 3.3 Unstop (`unstop.py`)

**What it scrapes:** Competitions and hackathons from [unstop.com](https://unstop.com/hackathons) (formerly Dare2Compete)

**Technique:** StealthyFetcher. Unstop is an Angular SPA requiring JavaScript rendering.

**CSS Selectors Used:**

| Field | Selector | Notes |
|-------|----------|-------|
| Card container | `a[class*="opp_"]` | Fallback: `a[class*="item"]` or `[class*="card"]` |
| Title | `h3[itemprop="name"]` | Fallback: `h3.double-wrap`, then any `h3` |
| Link | `href` on the `<a>` tag | Prepends `https://unstop.com` if relative |
| Organization | `p.single-wrap` | Company/organizer name |
| Deadline | `div.dates-fields label.tag-text` | Handles "X days left" and "Posted Aug 19" |
| Tags | `span.chip_text` | Competition categories |
| Location | `span.location_text` | City/region |

**Special Parsing:**
- `_extract_deadline_from_days_left()` converts "5 days left" to an actual date using `datetime.now() + timedelta(days=5)`
- `_determine_type()` auto-detects Internship/Certification from title keywords

**Known Limitations:**
- "X days left" approximation can be off by hours depending on time of day
- Login required for full eligibility details
- Some cards use inconsistent class naming

**Test independently:**
```bash
python scripts/scrapers/unstop.py
```

---

### 3.4 HackerEarth (`hackerearth.py`)

**What it scrapes:** Coding challenges from [hackerearth.com/challenges](https://www.hackerearth.com/challenges/)

**Technique:** StealthyFetcher. HackerEarth is a Next.js app with SSR, but uses virtual scrolling.

**CSS Selectors Used:**

| Field | Selector | Notes |
|-------|----------|-------|
| Card container | `div.group.relative.w-full.block` | Exact Tailwind class combo |
| Title | `h3` | Challenge name |
| Link | First `a[href]` containing `/challenges/` | Walks up to `div.group` ancestor |
| Status | `div.inline-flex span` | Live / Registration Open / Upcoming |
| Participants | `div.flex.items-center span` | Numeric or "K" suffix |
| Company | `div.text-muted-foreground` | Hiring company name |

**Two-Pass Strategy:**
1. **Strategy 1:** Exact Tailwind class selector `div.group.relative.w-full.block` for above-the-fold cards
2. **Strategy 2:** If fewer than 10 results, searches all `a[href*="/challenges/"]` links and walks up to find card ancestors (catches cards with reordered class lists)

**Known Limitations:**
- **Virtual scrolling:** Only 3–5 above-the-fold cards are in the initial HTML. The rest load dynamically as the user scrolls. StealthyFetcher does not scroll, so the listing is incomplete.
- **No deadlines on listing page** — only status badges (Live/Upcoming). Deadlines are only available on detail pages (handled by enrichment).
- No prize data on listing page

**Test independently:**
```bash
python scripts/scrapers/hackerearth.py
```

---

### 3.5 Internshala (`internshala.py`)

**What it scrapes:** Internships from [internshala.com/internships](https://internshala.com/internships)

**Technique:** StealthyFetcher. Internshala is a heavy SPA with aggressive anti-bot measures.

**CSS Selectors Used:**

| Field | Selector | Notes |
|-------|----------|-------|
| Card container | `[class*="internship"]` | Fallback: `[class*="card"]`, `[class*="listing"]` |
| Title | `h3::text`, `h4::text`, `h5::text`, `a::text` | First heading with text > 3 chars |
| Link | `a[href*='/internship/']` | Prepends `https://internshala.com` |
| Company | `[class*='company']::text` | Company name |
| Stipend | Recursive text search for `₹` | Regex: `₹\s*[\d,]+` |
| Location | `[class*='location']::text` | City/Work from home |
| Duration | Recursive text search for `\d+ (month\|week\|day)` | e.g. "6 months" |

**Known Limitations:**
- No deadline data on listing page
- Aggressive bot detection — may occasionally fail with status 403
- Login may be required for full results
- Selector matching is broad (class partial matching) which can produce false positives

**Test independently:**
```bash
python scripts/scrapers/internshala.py
```

---

## 4. Multi-Source Framework

### How `sources.json` Works

`scripts/scrapers/sources.json` is a registry of 50 sources. Each source is a JSON object with metadata, selectors, and fetch configuration. The multi-source framework (`multi_source.py`) reads this registry and dispatches to the appropriate fetching strategy.

**Registry structure:**
```json
{
  "version": "1.0.0",
  "last_updated": "2026-08-20",
  "total_sources": 50,
  "sources": [ ... ],
  "scrape_methods": { ... },
  "regions": { ... }
}
```

### How to Add a New Source

Add an entry to the `sources` array:

```json
{
  "id": "my_platform",
  "name": "My Platform",
  "url": "https://myplatform.com/listings",
  "type": "hackathon",
  "category": "direct_host",
  "scrape_method": "scrapling",
  "selectors": {
    "item": ".listing-card",
    "title": ".card-title",
    "link": ".card-title a",
    "deadline": ".card-date",
    "location": ".card-location",
    "prize": ".prize-amount",
    "participants": ".participant-count",
    "tags": ".card-tags span",
    "status": ".card-status"
  },
  "enabled": true,
  "priority": "medium",
  "region": "global",
  "notes": "Description of the platform and scraping considerations"
}
```

**Required fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (snake_case) |
| `name` | string | Display name |
| `url` | string | Listing page URL to scrape |
| `type` | string | `hackathon`, `internship`, or `certification` |
| `scrape_method` | string | `scrapling`, `httpx`, or `api` |
| `selectors.item` | string | CSS selector for individual cards/entries |
| `enabled` | boolean | Whether to include in multi-source runs |

**Optional selector fields:** `title`, `link`, `deadline`, `location`, `prize`, `participants`, `tags`, `status`, `image`

**Optional metadata fields:** `category` (aggregator/direct_host/corporate/government/university), `priority` (high/medium/low), `region` (global/india/us/eu), `notes`

### The 3 Scrape Methods

#### 1. `scrapling` — Headless Browser (JS-rendered SPAs)

```python
# Used for: React/Vue/Angular SPAs, sites requiring JavaScript
# Dependencies: scrapling[fetchers], patchright (Chromium)
page = StealthyFetcher.fetch(url, headless=True, disable_resources=True, network_idle=True, timeout=30000)
cards = page.css(card_selector)
```

**When to use:** Sites that load content dynamically, use React/Vue/Angular, or have anti-bot measures that basic HTTP requests trigger.

**Pros:** Handles any JS-rendered content, bypasses most anti-bot measures
**Cons:** Slow (spawns Chromium), high memory usage, requires Chromium installed

#### 2. `httpx` — Static HTML (Server-rendered pages)

```python
# Used for: Server-rendered HTML, Rails/Django/WordPress sites
resp = httpx.get(url, follow_redirects=True, timeout=30, headers={...})
page = Adaptor(resp.text, url=url)  # Parse with scrapling's Adaptor
cards = page.css(card_selector)
```

**When to use:** Sites that render HTML on the server (Rails, Django, WordPress, static generators). Faster than scrapling.

**Pros:** Fast, lightweight, no browser needed
**Cons:** Cannot handle JS-rendered content, may be blocked by anti-bot

#### 3. `api` — Direct API Calls (JSON endpoints)

```python
# Used for: Sites with public/internal JSON APIs
resp = httpx.get(url, headers={"Accept": "application/json"})
data = resp.json()
# Tries: top-level list, {"data": [...]}, {"results": [...]}, {"nodes": [...]}
```

**When to use:** Sites with GraphQL APIs, REST endpoints, or JSON data feeds.

**Pros:** Fastest, most reliable, structured data
**Cons:** APIs may change without notice, may require auth, response structure varies wildly

**Auto-detection patterns for API responses:**
- Top-level list: `[...]`
- Wrapped list: `{"data": [...]}`, `{"results": [...]}`, `{"items": [...]}`, `{"hackathons": [...]}`
- GraphQL/Relay: `{"nodes": [...]}`, `{"edges": [{"node": {...}}]}`

### How to Test a New Source

```bash
# 1. List all sources and their status
npm run scrape:sources

# 2. Run a specific source
python scripts/scrapers/run_all.py --source my_platform

# 3. Run with verbose logging
python scripts/scrapers/run_all.py --source my_platform --verbose

# 4. Test directly with multi_source.py
python scripts/scrapers/multi_source.py --source my_platform --verbose
```

---

## 5. Enrichment Pipeline

### What `enrich.py` Does

The enrichment pipeline is a Tier-2 scraper that visits individual opportunity detail pages to fill in missing data. It runs after the initial listing scrape and targets items with quality scores below a configurable threshold (default: 50).

### How It Works

1. **Load** — Reads `data/scraped_opportunities.json`
2. **Filter** — Identifies items where `quality_score(item) < threshold`
3. **Dispatch** — Detects the source platform from the item's URL
4. **Fetch** — Visits the detail page with `StealthyFetcher`
5. **Extract** — Runs source-specific extraction logic for each platform
6. **Update** — Merges extracted fields into the existing item
7. **Save** — Writes enriched data back to disk

### Platform-Specific Extractors

| Platform | Extractor Function | Fields Extracted |
|----------|--------------------|------------------|
| Devfolio | `_extract_devfolio()` | deadline, location, prize_pool, eligibility, participants |
| Devpost | `_extract_devpost()` | deadline, location, prize_pool, eligibility, participants |
| HackerEarth | `_extract_hackerearth()` | deadline, prize_pool, participants, eligibility |
| Unknown | — | Skipped (no extractor available) |

### Extraction Techniques

Each extractor uses regex pattern matching against the full page text:

**Deadline extraction patterns:**
```python
r'(?:deadline|due|closes?|ends?)\s*(?:on|:)?\s*(\w+\s+\d{1,2},?\s*\d{4})'
r'(\d{1,2})/(\d{1,2})/(\d{2,4})'
r'(\d{4}-\d{2}-\d{2})'
```

**Prize extraction patterns:**
```python
r'(?:prize|pool|total|worth)\s*(?:pool)?\s*(?:worth)?\s*\$\s*([\d,]+(?:\.\d+)?)'
r'(?:prize|reward)\s*(?:worth)?\s*(?:INR|₹)\s*([\d,]+(?:\.\d+)?)'
```

**Location classification:**
- "online" + "offline/in-person" → Hybrid
- "offline/in-person/on-site" → Offline
- "virtual/remote/online" → Online (default)

### Running Independently

```bash
# Enrich all items below score 50
python scripts/scrapers/enrich.py

# Preview without making changes
python scripts/scrapers/enrich.py --dry-run

# Enrich below a higher threshold (70)
python scripts/scrapers/enrich.py --threshold 70

# Verbose logging
python scripts/scrapers/enrich.py --dry-run --verbose
```

### Quality Score Thresholds

| Threshold | Behavior |
|-----------|----------|
| `< 30` | Severely incomplete — likely only title + link |
| `< 50` | Default enrichment target — missing 3+ key fields |
| `< 70` | Moderate — has basics but missing prizes/location |
| `≥ 70` | Good quality — enrichment skipped |

### Rate Limiting

The enrichment pipeline enforces a **2-second delay** between requests (`REQUEST_DELAY = 2.0`) to avoid overwhelming target servers.

---

## 6. Data Schema

### ScrapeItem (Python) — `base.py`

```python
@dataclass
class ScrapeItem:
    title: str                    # Required
    type: str                     # "Hackathon" | "Internship" | "Certification"
    source: str                   # Platform name (e.g. "Devfolio")
    link: str                     # URL to opportunity
    deadline: str                 # YYYY-MM-DD format
    eligibility: str              # Who can apply
    tags: list[str]               # Freeform tags
    notes: str                    # Additional context
    date_added: str               # YYYY-MM-DD (auto-populated)
    location: str                 # "Online" | "Hybrid" | "Offline"
    prize_pool: str               # e.g. "$10,000", "₹1,00,000"
    participants: str             # e.g. "500", "1.2K"
    organizer: str                # Host/organizer name
    duration: str                 # e.g. "3 months", "48 hours"
```

**Computed property:**
```python
@property
def fingerprint(self) -> str:
    """SHA-256(title + source + type) truncated to 12 chars."""
    raw = f"{self.title.lower().strip()}|{self.source.lower().strip()}|{self.type.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]
```

### Opportunity (TypeScript) — `src/types/opportunity.ts`

```typescript
export interface Opportunity {
  id: string;                    // e.g. "seed_001" or generated
  title: string;
  type: OpportunityType;         // "Hackathon" | "Internship" | "Certification"
  source: string;
  link: string;
  deadline: string;              // YYYY-MM-DD
  eligibility: string;
  tags: string[];
  status: OpportunityStatus;     // "Not Started" | "Applied" | "In Progress" | "Rejected" | "Completed"
  notes: string;
  date_added: string;            // YYYY-MM-DD
  location?: string;
  prize_pool?: string;
  participants?: string;
  organizer?: string;
  duration?: string;
  quality_score?: number;        // 0-100
}
```

### Field Mapping: Python → JSON → TypeScript

| ScrapeItem (Python) | scraped_opportunities.json | Opportunity (TypeScript) | Notes |
|---------------------|---------------------------|--------------------------|-------|
| `title` | `title` | `title` | Direct copy |
| `type` | `type` | `type` | Validated: Hackathon/Internship/Certification |
| `source` | `source` | `source` | Platform display name |
| `link` | `link` | `link` | Full URL required |
| `deadline` | `deadline` | `deadline` | YYYY-MM-DD or empty |
| `eligibility` | `eligibility` | `eligibility` | Free text |
| `tags` | `tags` | `tags` | String array |
| `notes` | `notes` | `notes` | Free text |
| `date_added` | `date_added` | `date_added` | Auto-populated on scrape |
| `location` | `location` | `location` | Auto-classified if empty |
| `prize_pool` | `prize_pool` | `prize_pool` | Optional |
| `participants` | `participants` | `participants` | Optional |
| `organizer` | `organizer` | `organizer` | Optional |
| `duration` | `duration` | `duration` | Optional |
| `fingerprint` | `fingerprint` | — | Python-only; used for dedup; not in TS |
| — | — | `id` | Generated as `seed_NNN` during merge |
| — | — | `status` | Defaults to `"Not Started"` |
| — | — | `quality_score` | Computed by `quality_score()` |

---

## 7. Pipeline Commands

### All npm Scripts

| Command | Python Equivalent | What It Does |
|---------|-------------------|--------------|
| `npm run scrape` | `python scripts/scrapers/run_all.py` | Full pipeline: all 5 scrapers, dedup, score, validate, save |
| `npm run scrape:quick` | `run_all.py --quick` | Listing pages only — no enrichment |
| `npm run scrape:detailed` | `run_all.py --detailed` | Scrape + enrich low-quality items |
| `npm run scrape:devfolio` | `run_all.py --devfolio` | Devfolio only |
| `npm run scrape:devpost` | `run_all.py --devpost` | Devpost only |
| `npm run scrape:unstop` | `run_all.py --unstop` | Unstop only |
| `npm run scrape:hackerearth` | `run_all.py --hackerearth` | HackerEarth only |
| `npm run scrape:internshala` | `run_all.py --internshala` | Internshala only |
| `npm run scrape:multi` | `run_all.py --multi` | Multi-source from sources.json (50 platforms) |
| `npm run scrape:enrich` | `run_all.py --enrich` | Enrich existing data only (no scraping) |
| `npm run scrape:quality` | `run_all.py --quality` | Score quality on existing data |
| `npm run scrape:validate` | `run_all.py --validate` | Validate existing JSON |
| `npm run scrape:sources` | `multi_source.py --list` | List all registered sources |
| `npm run merge:seeds` | `python scripts/merge_seeds.py` | Generate SEED_DATA entries from scraped JSON |
| `npm run validate` | `node scripts/validate-data.mjs` | Validate SEED_DATA in storage.ts |
| `npm run validate:links` | `validate-data.mjs --check-links` | HTTP-check all links |

### Common Workflows

#### Daily scraping
```bash
npm run scrape                    # Quick full scrape
# Review data/scraped_opportunities.json
npm run merge:seeds               # Generate TS entries
# Review data/new_seed_entries.ts → copy to storage.ts
npm run validate                  # Ensure SEED_DATA is valid
npm run build                     # Build the app
```

#### Deep scrape with enrichment
```bash
npm run scrape:detailed           # Scrape + enrich low-quality items
# Takes longer due to detail page visits
```

#### Add a new source from sources.json
```bash
# 1. Edit sources.json, add entry
# 2. Test it
python scripts/scrapers/multi_source.py --source my_platform --verbose
# 3. Run full pipeline with multi
npm run scrape:multi
# 4. Merge
npm run merge:seeds
```

#### Quality audit
```bash
npm run scrape:quality            # Score all items, print summary
# Review the quality summary in output
```

---

## 8. Quality System

### How `quality_score()` Works

Each `ScrapeItem` is scored on a 0–100 scale based on field completeness. The scoring is defined in `base.py:164-200`.

### Scoring Breakdown

| Field | Points | Scoring Logic |
|-------|--------|---------------|
| `title` | 20 | Non-empty string |
| `type` | 10 | Non-empty string |
| `link` | 15 | Non-empty string |
| `deadline` | 15 | Non-empty string |
| `eligibility` | 10 | Non-empty string |
| `tags` | 5 | Non-empty array |
| `location` | 10 | Non-empty string |
| `prize_pool` | 5 | Non-empty string |
| `participants` | 5 | Non-empty string |
| `organizer` | 5 | Non-empty string |
| **Total** | **100** | |

### Score Interpretation

| Range | Rating | Typical Content |
|-------|--------|-----------------|
| 90–100 | Excellent | Full detail from listing or enriched |
| 70–89 | Good | Has most fields, missing 1–2 optional |
| 50–69 | Moderate | Has title, link, type, maybe deadline |
| 30–49 | Low | Missing multiple key fields |
| 0–29 | Poor | Likely only title + link |

### How to Improve Quality Scores

1. **Enrich** — Run `npm run scrape:detailed` or `npm run scrape:enrich` to visit detail pages
2. **Better selectors** — Update CSS selectors in built-in scrapers to capture more fields from listing pages
3. **Add to sources.json** — Sources with more selectors (`prize`, `participants`, `tags`) produce higher-scoring items
4. **Manual enrichment** — For important items, manually fill in missing fields in `storage.ts`

---

## 9. Staleness Detection

### How Stale Entries Are Detected

The validation script (`validate-data.mjs`) detects stale entries by checking:

```javascript
if (seed.deadline < today && seed.status === 'Not Started') {
  warnings.push(`[${id}] deadline has passed but status is still 'Not Started'`);
}
```

**Rule:** An entry is considered **potentially stale** when:
- Its `deadline` date has passed (is before today)
- Its `status` is still `"Not Started"`

### Grace Periods

There is no configurable grace period in the current implementation. The check is a strict date comparison:

```
today = 2026-08-20
deadline = 2026-08-19 → STALE
deadline = 2026-08-20 → NOT STALE (equal to today)
deadline = 2026-08-21 → NOT STALE
```

### Auto-Completion

The system does **not** auto-complete or auto-remove stale entries. Stale entries produce warnings during validation but are not automatically updated. The user must manually:

1. Mark as `status: 'Completed'` if the opportunity was pursued
2. Update the `deadline` if it was extended
3. Remove the entry if the opportunity is permanently closed

### Staleness Prevention

- **Scrapers filter expired items:** Each scraper's selectors typically exclude "ended", "past", "closed" items
- **`parse_deadline()` filters dead states:** Returns empty string for "Ended", "Past", "Expired", "Closed"
- **Unstop handles relative dates:** "5 days left" is converted to an absolute date, naturally expiring

---

## 10. Source Directory

### Currently Enabled Sources (50 in sources.json)

#### Priority: HIGH

| ID | Name | Type | Region | Method | Category |
|----|------|------|--------|--------|----------|
| `devpost` | Devpost | hackathon | global | scrapling | aggregator |
| `devfolio` | Devfolio | hackathon | global | scrapling | aggregator |
| `unstop` | Unstop | hackathon | india | scrapling | aggregator |
| `hackerearth` | HackerEarth | hackathon | global | scrapling | direct_host |
| `mlh` | MLH | hackathon | global | httpx | aggregator |
| `dorahacks` | DoraHacks | hackathon | global | scrapling | direct_host |
| `ethglobal` | ETHGlobal | hackathon | global | scrapling | direct_host |
| `lablab_ai` | lablab.ai | hackathon | global | scrapling | direct_host |
| `hack2skill` | Hack2Skill | hackathon | india | scrapling | aggregator |
| `internshala` | Internshala | internship | india | scrapling | aggregator |
| `kaggle` | Kaggle | hackathon | global | api | direct_host |
| `sih` | Smart India Hackathon | hackathon | india | httpx | government |
| `challenge_gov` | Challenge.gov | hackathon | us | httpx | government |
| `tcs_codevita` | TCS CodeVita | hackathon | india | httpx | corporate |
| `google_careers` | Google Careers | internship | global | scrapling | corporate |
| `amazon_jobs` | Amazon Jobs | internship | global | scrapling | corporate |
| `microsoft_careers` | Microsoft Careers | internship | global | scrapling | corporate |
| `linkedin_jobs` | LinkedIn Jobs | internship | global | scrapling | aggregator |
| `indeed` | Indeed | internship | us | scrapling | aggregator |
| `yc_jobs` | YC Work at a Startup | internship | us | scrapling | corporate |
| `usajobs` | USAJOBS | internship | us | httpx | government |
| `nasa_internships` | NASA Internships | internship | us | httpx | government |
| `nsf_reu` | NSF REU | fellowship | us | httpx | government |
| `forage` | Forage | internship | global | scrapling | corporate |
| `nptel` | NPTEL | certification | india | httpx | university |
| `swayam` | SWAYAM | certification | india | httpx | government |
| `buddy4study` | Buddy4Study | scholarship | india | scrapling | aggregator |

#### Priority: MEDIUM

| ID | Name | Type | Region | Method | Category |
|----|------|------|--------|--------|----------|
| `techgig` | TechGig | hackathon | india | httpx | corporate |
| `codeforces` | Codeforces | hackathon | global | httpx | direct_host |
| `hackerrank` | HackerRank | certification | global | scrapling | direct_host |
| `leetcode` | LeetCode | hackathon | global | api | direct_host |
| `coursera` | Coursera | certification | global | scrapling | aggregator |
| `edx` | edX | certification | global | scrapling | university |
| `goldman_sachs` | Goldman Sachs | internship | global | httpx | corporate |
| `jpmorgan` | JPMorgan Chase | internship | global | scrapling | corporate |
| `flipkart` | Flipkart | internship | india | scrapling | corporate |
| `hackwithinfy` | HackWithInfy | hackathon | india | httpx | corporate |
| `wellfound` | Wellfound | internship | global | scrapling | aggregator |
| `handshake` | Handshake | internship | us | scrapling | university |
| `daad_rise` | DAAD RISE | fellowship | eu | httpx | government |
| `mitacs` | Mitacs | fellowship | global | httpx | government |
| `cern_internships` | CERN Internships | internship | eu | httpx | corporate |
| `virtual_internships` | Virtual Internships | internship | global | scrapling | aggregator |
| `aiesec` | AIESEC | internship | global | scrapling | university |
| `analytics_vidhya` | Analytics Vidhya DataHack | hackathon | india | scrapling | direct_host |
| `machinehack` | MachineHack | hackathon | india | scrapling | direct_host |
| `angelhack` | AngelHack | hackathon | global | httpx | direct_host |
| `hackindia` | HackIndia | hackathon | india | httpx | aggregator |
| `reskilll` | Reskilll | hackathon | india | scrapling | aggregator |
| `skillenza` | Skillenza | hackathon | india | scrapling | corporate |

### Research Directory (195+ platforms catalogued)

The full research is documented in `PLATFORMS_RESEARCH.md` with 195+ platforms across 12 categories:

| Category | Count | Example Platforms |
|----------|-------|-------------------|
| Online Certification | 30 | Coursera, edX, Udemy, Khan Academy |
| India MOOC/Certification | 6 | SWAYAM, NPTEL, DIKSHA |
| Scholarship Aggregators | 24 | Buddy4Study, Fastweb, BigFuture |
| Government Scholarships (India) | 10 | NSP, UP Portal, Maharashtra DBT |
| Government Scholarships (Intl) | 20 | FAFSA, Erasmus Mundus, DAAD, Chevening |
| Fellowship Programs | 15 | Echoing Green, Thiel, Ashoka |
| Open Source Training | 17 | GSoC, MLH Fellowship, LFX, Outreachy |
| Industry Certifications | 16 | AWS, Azure, Google Cloud, Salesforce |
| Corporate Training | 10 | McKinsey Forward, Microsoft LEAP |
| Research Grants | 17 | Grants.gov, NIH Reporter, NSF Awards |
| Additional/Meta-Platforms | 15 | Unstop, Class Central, Studyportals |
| Niche/Regional | 15 | Study in Sweden, Eklavya Scholars |

### API Availability Summary

| API Type | Count | Notable |
|----------|-------|---------|
| Official API | ~18 | Coursera, AWS, Microsoft, Google Cloud, Grants.gov, GSoC |
| Scrapable (public HTML) | ~25 | edX, SWAYAM, NPTEL, Buddy4Study, DAAD |
| No API (manual only) | ~152 | Government portals, fellowship sites, most scholarships |

---

## 11. Troubleshooting

### Common Errors

#### `ModuleNotFoundError: No module named 'scrapling'`
```bash
pip install "scrapling[fetchers]"
patchright install chromium
```

#### `ModuleNotFoundError: No module named 'httpx'`
```bash
pip install httpx
```

#### `Scraper X failed after X.Xs: ...`
The scraper hit an error (network timeout, selector mismatch, anti-bot). Check:
1. Is the target site up?
2. Have selectors changed? (inspect the page's HTML)
3. Is Chromium installed? (`patchright install chromium`)
4. Try with `--verbose` flag for detailed error output

#### `No cards matched '.selector'`
The CSS selector doesn't match any elements. This usually means the site's HTML structure changed. Steps:
1. Visit the URL in a browser, inspect the listing page HTML
2. Identify the new card container selector
3. Update the selector in the scraper or `sources.json`
4. Test with `--verbose`

#### `HTTP 403` or `HTTP 429`
Rate limiting or anti-bot protection. Mitigations:
1. Increase delay between requests (edit `REQUEST_DELAY` in `enrich.py`)
2. Add rotation headers
3. Use `scrapling` method instead of `httpx`
4. Reduce scrape frequency

#### `Validate: deadline '...' is not a valid YYYY-MM-DD date`
The scraper produced a deadline in an unexpected format. Check:
1. The `parse_deadline()` function in `base.py` — add the new format
2. The scraper's date extraction logic

#### `Validate: duplicate title with ...`
Two items have the same title (case-insensitive). Usually a cross-source duplicate that escaped fingerprinting. The dedup uses `title|source|type` so the same title from different sources is allowed.

### Debugging a Broken Scraper

```bash
# 1. Run the scraper standalone with verbose output
python scripts/scrapers/myplatform.py 2>&1

# 2. Or via run_all.py
python scripts/scrapers/run_all.py --source myplatform --verbose

# 3. Test the multi-source version
python scripts/scrapers/multi_source.py --source myplatform --verbose

# 4. Check what the page actually returns
python -c "
from scrapling.fetchers import StealthyFetcher
page = StealthyFetcher.fetch('https://example.com', headless=True)
print(f'Status: {page.status}')
print(f'HTML length: {len(str(page.html_content))}')
cards = page.css('.my-selector')
print(f'Cards found: {len(cards)}')
for c in cards[:3]:
    print(f'  {c.text[:80]}...')
"
```

### Handling Rate Limiting

1. **Increase delays:** Edit `REQUEST_DELAY` in `enrich.py` (default 2.0s)
2. **Reduce concurrent scrapes:** Run individual scrapers instead of all at once
3. **Use httpx over scrapling** when possible (faster, lighter)
4. **Monitor HTTP status codes:** 429 = rate limited, 403 = blocked
5. **Run during off-peak hours** for the target platform's timezone

---

## 12. Future Roadmap

### Planned Features

- [ ] **Scroll simulation** — Add scroll-to-bottom for HackerEarth and other infinite-scroll sites
- [ ] **Headless cookie persistence** — Maintain session state across enrichment requests
- [ ] **Source health monitoring** — Track scraper success rates, alert on selector breakage
- [ ] **Diff-based updates** — Only re-scrape sources that have changed since last run
- [ ] **GraphQL source support** — First-class support for GraphQL APIs in sources.json
- [ ] **Enrichment for all sources** — Add extractors for Unstop, Internshala, and all sources.json platforms
- [ ] **Automated SEED_DATA merge** — CI/CD pipeline to auto-merge high-confidence entries
- [ ] **Quality score weighting** — Weight scores by field importance (deadline > participants)
- [ ] **Staleness auto-update** — Automatically mark past-deadline items as "Completed" or "Expired"
- [ ] **Multi-page pagination** — Handle paginated listing pages across all scrapers
- [ ] **Image/logo extraction** — Pull event logos for richer UI display
- [ ] **Dedup across runs** — Persist fingerprints to avoid re-adding removed items

### How to Contribute

1. **Add a new source:** Edit `sources.json` and test with `npm run scrape:multi`
2. **Fix a broken scraper:** Update CSS selectors in the relevant `.py` file
3. **Add an enrichment extractor:** Add a `_extract_myplatform()` function to `enrich.py`
4. **Improve quality scores:** Add field extraction for `prize_pool`, `participants`, `organizer`
5. **Add to research:** Update `PLATFORMS_RESEARCH.md` with new platform entries

---

## Appendix A: File Structure

```
scripts/
  scrapers/
    __init__.py              # Package exports
    base.py                  # ScrapeItem, parse_deadline, quality_score, deduplicate, classify_location
    devfolio.py              # Devfolio scraper (StealthyFetcher)
    devpost.py               # Devpost scraper (StealthyFetcher)
    unstop.py                # Unstop scraper (StealthyFetcher)
    hackerearth.py           # HackerEarth scraper (StealthyFetcher)
    internshala.py           # Internshala scraper (StealthyFetcher)
    multi_source.py          # Dynamic source dispatcher (sources.json)
    enrich.py                # Tier-2 detail page enrichment
    run_all.py               # Pipeline orchestrator
    sources.json             # Source registry (50 platforms)
    test_devpost.py          # Devpost scraper tests
    test_hackerearth.py      # HackerEarth scraper tests
    test_unstop.py           # Unstop scraper tests
  merge_seeds.py             # scraped JSON → SEED_DATA TS entries
  validate-data.mjs          # SEED_DATA validation (Node.js)
data/
  scraped_opportunities.json # Raw scraped output (gitignored)
  new_seed_entries.json      # New entries for review (gitignored)
  new_seed_entries.ts        # TypeScript entries for merge (gitignored)
src/
  types/opportunity.ts       # Opportunity TypeScript interface
  lib/storage.ts             # SEED_DATA array and storage logic
```

## Appendix B: Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| — | — | No environment variables currently required |

All configuration is done via CLI arguments and `sources.json`.

## Appendix C: Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `scrapling[fetchers]` | latest | Headless browser scraping (StealthyFetcher + Adaptor) |
| `httpx` | latest | HTTP client for static HTML and API calls |
| `patchright` | (via scrapling) | Chromium browser automation |
| Python | 3.13+ | Runtime |
| Node.js | 18+ | Validation scripts and build |
