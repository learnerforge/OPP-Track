"""
run_all.py — Orchestrator that runs all scrapers and outputs scraped_opportunities.json.

Pipeline:
    1. Scrape (existing 5 scrapers + multi-source if --multi)
    2. Deduplicate
    3. Quality score all items
    4. Classify locations
    5. Enrich low-score items (if --detailed or --enrich)
    6. Validate
    7. Save

Usage:
    python scripts/scrapers/run_all.py                  # Full pipeline
    python scripts/scrapers/run_all.py --detailed       # Enrich low-quality items after scraping
    python scripts/scrapers/run_all.py --quick          # Scrape listing pages only, no enrichment
    python scripts/scrapers/run_all.py --enrich         # Enrich existing data only (no scraping)
    python scripts/scrapers/run_all.py --quality        # Run quality scoring on existing data
    python scripts/scrapers/run_all.py --multi          # Include multi-source scrapers from sources.json
    python scripts/scrapers/run_all.py --source devfolio  # Run only a specific source
    python scripts/scrapers/run_all.py --validate       # Validate existing JSON only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scrapers.base import ScrapeItem, deduplicate, deduplicate_by_link, quality_score, classify_location
from scripts.scrapers.devfolio import scrape_devfolio
from scripts.scrapers.devpost import scrape_devpost
from scripts.scrapers.unstop import scrape_unstop
from scripts.scrapers.hackerearth import scrape_hackerearth
from scripts.scrapers.internshala import scrape_internshala

OUTPUT_FILE = PROJECT_ROOT / "data" / "scraped_opportunities.json"
SOURCES_FILE = PROJECT_ROOT / "scripts" / "scrapers" / "sources.json"
ENRICH_THRESHOLD = 50

SCRAPERS = {
    "devfolio": ("Devfolio", scrape_devfolio),
    "devpost": ("Devpost", scrape_devpost),
    "unstop": ("Unstop", scrape_unstop),
    "hackerearth": ("HackerEarth", scrape_hackerearth),
    "internshala": ("Internshala", scrape_internshala),
}


def _load_multi_sources() -> dict[str, dict]:
    """Load sources.json and return {id: source_config} for enabled sources."""
    if not SOURCES_FILE.exists():
        return {}
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        s["id"]: s
        for s in data.get("sources", [])
        if s.get("enabled", True)
    }


def run_scraper(name: str, func) -> list[ScrapeItem]:
    """Run a single scraper with error handling and timing."""
    logging.info(f"--- Running {name} scraper ---")
    t0 = time.time()
    try:
        results = func()
        elapsed = time.time() - t0
        logging.info(f"    {name} finished in {elapsed:.1f}s — {len(results)} items")
        return results
    except Exception as e:
        elapsed = time.time() - t0
        logging.error(f"Scraper {name} failed after {elapsed:.1f}s: {e}")
        return []


def run_multi_source_scraper(source_id: str, source_config: dict) -> list[ScrapeItem]:
    """Attempt to scrape a source from sources.json via multi_source module."""
    try:
        from scripts.scrapers.multi_source import scrape_source
        t0 = time.time()
        logging.info(f"--- Running multi-source: {source_config.get('name', source_id)} ---")
        results = scrape_source(source_id, source_config)
        elapsed = time.time() - t0
        logging.info(f"    {source_id} finished in {elapsed:.1f}s — {len(results)} items")
        return results
    except ImportError:
        logging.warning(
            f"multi_source.py not found — cannot scrape {source_id}. "
            "Create scripts/scrapers/multi_source.py to enable additional sources."
        )
        return []
    except Exception as e:
        logging.error(f"Multi-source scraper {source_id} failed: {e}")
        return []


def score_items(items: list[ScrapeItem]) -> list[ScrapeItem]:
    """Calculate quality scores and classify locations for all items."""
    for item in items:
        item.location = item.location or classify_location(
            f"{item.title} {item.eligibility} {item.notes}"
        )
    return items


def enrich_low_quality(items: list[ScrapeItem], threshold: int = ENRICH_THRESHOLD) -> list[ScrapeItem]:
    """Enrich items below the quality threshold by visiting detail pages.

    Saves current items to disk, runs enrich_items, then reloads.
    """
    # Save current items so enrich can read them
    output_path = OUTPUT_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([item.to_dict() for item in items], f, indent=2, ensure_ascii=False)

    low_score_items = [item for item in items if quality_score(item) < threshold]
    logging.info(f"Enriching {len(low_score_items)} items below quality score {threshold}...")

    try:
        from scripts.scrapers.enrich import enrich_items
        enrich_items(dry_run=False, threshold=threshold)
    except Exception as e:
        logging.error(f"Enrichment failed: {e}")

    # Reload enriched data from disk
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            ScrapeItem(**{k: v for k, v in d.items() if k != "fingerprint"})
            for d in data
        ]
    return items


def validate_items(items: list[ScrapeItem]) -> tuple[list[ScrapeItem], list[dict]]:
    """Validate all items. Returns (valid_items, errors)."""
    valid = []
    errors = []
    for item in items:
        errs = item.validate()
        if errs:
            errors.append({"title": item.title, "source": item.source, "errors": errs})
        else:
            valid.append(item)
    return valid, errors


def print_quality_summary(items: list[ScrapeItem], threshold: int = ENRICH_THRESHOLD) -> None:
    """Print a summary of quality scores across all items."""
    if not items:
        return
    scores = [quality_score(item) for item in items]
    avg = sum(scores) / len(scores)
    below = [item for item in items if quality_score(item) < threshold]

    logging.info("\n─── Quality Summary ───")
    logging.info(f"  Total items:   {len(items)}")
    logging.info(f"  Avg score:     {avg:.1f}/100")
    logging.info(f"  Below {threshold}:    {len(below)}")

    if below:
        logging.info(f"\n  Lowest-scoring items:")
        for item in sorted(below, key=quality_score)[:10]:
            sc = quality_score(item)
            logging.info(f"    [{sc:3d}] {item.title} ({item.source})")


def main():
    parser = argparse.ArgumentParser(description="OPP-Track Scraper Orchestrator")

    # Scraper selection
    parser.add_argument("--devfolio", action="store_true", help="Run only Devfolio scraper")
    parser.add_argument("--devpost", action="store_true", help="Run only Devpost scraper")
    parser.add_argument("--unstop", action="store_true", help="Run only Unstop scraper")
    parser.add_argument("--hackerearth", action="store_true", help="Run only HackerEarth scraper")
    parser.add_argument("--internshala", action="store_true", help="Run only Internshala scraper")
    parser.add_argument("--multi", action="store_true", help="Include additional sources from sources.json")
    parser.add_argument("--source", type=str, default=None, help="Run only a specific source ID (from scrapers or sources.json)")

    # Pipeline control
    parser.add_argument("--detailed", action="store_true", help="After scraping, enrich items with low quality scores")
    parser.add_argument("--quick", action="store_true", help="Skip enrichment, just scrape listing pages")
    parser.add_argument("--enrich", action="store_true", help="Only run enrichment on existing scraped data (no scraping)")
    parser.add_argument("--quality", action="store_true", help="Run quality scoring on all items")
    parser.add_argument("--validate", action="store_true", help="Validate existing JSON only")

    # General
    parser.add_argument("--output", type=str, default=str(OUTPUT_FILE), help="Output JSON path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    output_path = Path(args.output)
    pipeline_start = time.time()

    # ── Validate-only mode ─────────────────────────────────────────
    if args.validate:
        if not output_path.exists():
            logging.error(f"File not found: {output_path}")
            sys.exit(1)
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = [ScrapeItem(**{k: v for k, v in d.items() if k != "fingerprint"}) for d in data]
        valid, errors = validate_items(items)
        logging.info(f"Validated {len(valid)} items, {len(errors)} errors")
        for err in errors:
            logging.warning(f"  {err['title']} ({err['source']}): {', '.join(err['errors'])}")
        sys.exit(1 if errors else 0)

    # ── Enrich-only mode ───────────────────────────────────────────
    if args.enrich:
        if not output_path.exists():
            logging.error(f"File not found: {output_path}")
            sys.exit(1)
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = [ScrapeItem(**{k: v for k, v in d.items() if k != "fingerprint"}) for d in data]
        items = enrich_low_quality(items)
        valid_items, errors = validate_items(items)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([item.to_dict() for item in valid_items], f, indent=2, ensure_ascii=False)
        print_quality_summary(valid_items)
        logging.info(f"\nSaved {len(valid_items)} enriched items to {output_path}")
        sys.exit(0)

    # ── Quality-only mode ──────────────────────────────────────────
    if args.quality:
        if not output_path.exists():
            logging.error(f"File not found: {output_path}")
            sys.exit(1)
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = [ScrapeItem(**{k: v for k, v in d.items() if k != "fingerprint"}) for d in data]
        items = score_items(items)
        print_quality_summary(items)
        # Write back with scores
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([item.to_dict() for item in items], f, indent=2, ensure_ascii=False)
        logging.info(f"\nUpdated quality scores for {len(items)} items")
        sys.exit(0)

    # ── Determine which scrapers to run ────────────────────────────
    source_flag = args.source
    has_scraper_flags = (
        args.devfolio or args.devpost or args.unstop
        or args.hackerearth or args.internshala
    )
    run_all_scrapers = not has_scraper_flags and not source_flag

    scraper_names: list[str] = []
    multi_source_ids: list[str] = []

    if source_flag:
        if source_flag in SCRAPERS:
            scraper_names = [source_flag]
        else:
            multi_source_ids = [source_flag]
    else:
        if has_scraper_flags:
            if args.devfolio:
                scraper_names.append("devfolio")
            if args.devpost:
                scraper_names.append("devpost")
            if args.unstop:
                scraper_names.append("unstop")
            if args.hackerearth:
                scraper_names.append("hackerearth")
            if args.internshala:
                scraper_names.append("internshala")
        else:
            scraper_names = list(SCRAPERS.keys())

    # Add multi-source if requested
    if args.multi or (source_flag and source_flag not in SCRAPERS):
        all_sources = _load_multi_sources()
        if source_flag and source_flag in all_sources:
            multi_source_ids = [source_flag]
        elif args.multi:
            multi_source_ids = [
                sid for sid in all_sources
                if sid not in SCRAPERS  # skip sources already covered by built-in scrapers
            ]

    # ── Scrape ─────────────────────────────────────────────────────
    all_items: list[ScrapeItem] = []
    scraper_timings: dict[str, float] = {}

    for name in scraper_names:
        label, func = SCRAPERS[name]
        t0 = time.time()
        results = run_scraper(name, func)
        scraper_timings[label] = time.time() - t0
        all_items.extend(results)
        logging.info(f"{label}: {len(results)} items")

    for sid in multi_source_ids:
        all_sources = _load_multi_sources()
        if sid in all_sources:
            t0 = time.time()
            results = run_multi_source_scraper(sid, all_sources[sid])
            scraper_timings[sid] = time.time() - t0
            all_items.extend(results)
            logging.info(f"{sid}: {len(results)} items")

    logging.info(f"\nTotal scraped items: {len(all_items)}")

    # ── Deduplicate ────────────────────────────────────────────────
    all_items = deduplicate(all_items)
    logging.info(f"After fingerprint dedup: {len(all_items)} items")
    all_items = deduplicate_by_link(all_items)
    logging.info(f"After link dedup: {len(all_items)} items")

    # ── Quality score + location classification ────────────────────
    all_items = score_items(all_items)
    scores = [quality_score(item) for item in all_items]
    avg_score = sum(scores) / len(scores) if scores else 0
    logging.info(f"Quality scores — avg: {avg_score:.1f}, range: {min(scores) if scores else 0}-{max(scores) if scores else 0}")

    # ── Enrichment ─────────────────────────────────────────────────
    if args.detailed and not args.quick:
        all_items = enrich_low_quality(all_items)
    elif not args.quick:
        logging.info("Skipping enrichment (use --detailed to enable)")

    # ── Validate ───────────────────────────────────────────────────
    valid_items, errors = validate_items(all_items)
    if errors:
        logging.warning(f"\nValidation errors ({len(errors)}):")
        for err in errors:
            logging.warning(f"  {err['title']} ({err['source']}): {', '.join(err['errors'])}")

    # ── Save output ────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = [item.to_dict() for item in valid_items]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logging.info(f"\nSaved {len(valid_items)} items to {output_path}")

    # ── Summary ────────────────────────────────────────────────────
    by_source: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for item in valid_items:
        by_source[item.source] = by_source.get(item.source, 0) + 1
        by_type[item.type] = by_type.get(item.type, 0) + 1

    logging.info("\nBy source:")
    for src, count in sorted(by_source.items()):
        logging.info(f"  {src}: {count}")
    logging.info("\nBy type:")
    for t, count in sorted(by_type.items()):
        logging.info(f"  {t}: {count}")

    # Quality summary
    print_quality_summary(valid_items)

    # Timing summary
    total_time = time.time() - pipeline_start
    logging.info("\n─── Timing ───")
    for name, elapsed in sorted(scraper_timings.items(), key=lambda x: -x[1]):
        logging.info(f"  {name}: {elapsed:.1f}s")
    logging.info(f"  Total pipeline: {total_time:.1f}s")


if __name__ == "__main__":
    main()
