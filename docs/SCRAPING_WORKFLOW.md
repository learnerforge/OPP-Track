# Scraping Workflow

OPP-Track uses [Scrapling](https://github.com/D4Vinci/Scrapling) to scrape hackathon, internship, and certification data from various platforms.

## Prerequisites

```bash
pip install "scrapling[fetchers]"
patchright install chromium
```

## Directory Structure

```
scripts/
  scrapers/
    __init__.py          # Package exports
    base.py              # ScrapeItem schema, utilities, dedup
    devfolio.py          # Devfolio hackathons (StealthyFetcher)
    devpost.py           # Devpost hackathons (StealthyFetcher)
    unstop.py            # Unstop hackathons + internships (StealthyFetcher)
    internshala.py       # Internshala internships (StealthyFetcher)
    run_all.py           # Orchestrator → data/scraped_opportunities.json
  merge_seeds.py         # Reads scraped JSON, generates SEED_DATA entries
data/
  scraped_opportunities.json   # Raw scraped output (gitignored)
  new_seed_entries.json        # New entries for review (gitignored)
  new_seed_entries.ts          # TypeScript entries for manual merge (gitignored)
```

## Usage

### Run all scrapers
```bash
npm run scrape
# or
python scripts/scrapers/run_all.py
```

### Run a single scraper
```bash
npm run scrape:devfolio
# or
python scripts/scrapers/run_all.py --devfolio
```

### Validate scraped data
```bash
npm run scrape:validate
```

### Preview new entries (deduplicated against existing SEED_DATA)
```bash
python scripts/merge_seeds.py --preview
```

### Generate merge file
```bash
npm run merge:seeds
```

## Workflow

1. **Scrape**: Run `npm run scrape` to fetch data from all sources
2. **Review**: Check `data/scraped_opportunities.json` for accuracy
3. **Preview**: Run `python scripts/merge_seeds.py --preview` to see new entries
4. **Merge**: Run `npm run merge:seeds` to generate TypeScript entries
5. **Manual**: Copy entries from `data/new_seed_entries.ts` into `src/lib/storage.ts` SEED_DATA array
6. **Bump**: Increment `SEED_VERSION` in `storage.ts`
7. **Validate**: Run `npm run validate` and `npm test`
8. **Commit**: `npm run build` then commit

## Source Protection Levels

| Source     | Fetcher         | JS Required | Notes                          |
|------------|-----------------|-------------|--------------------------------|
| Devfolio   | StealthyFetcher | Yes         | Next.js SPA, themes + dates    |
| Devpost    | StealthyFetcher | Yes         | React SPA                      |
| Unstop     | StealthyFetcher | Yes         | Cookies + JS required          |
| Internshala| StealthyFetcher | Yes         | Heavy SPA, login-gated         |

## Output Schema

Each scraper produces `ScrapeItem` objects matching the `Opportunity` TypeScript type:

```json
{
  "title": "string",
  "type": "Hackathon | Internship | Certification",
  "source": "string",
  "link": "string",
  "deadline": "YYYY-MM-DD",
  "eligibility": "string",
  "tags": ["string"],
  "notes": "string",
  "date_added": "YYYY-MM-DD",
  "fingerprint": "string (auto-generated hash for dedup)"
}
```
