"""
run_all.py — Orchestrator that runs all scrapers and outputs scraped_opportunities.json.

Usage:
    python scripts/scrapers/run_all.py              # Run all scrapers
    python scripts/scrapers/run_all.py --devfolio   # Run only Devfolio scraper
    python scripts/scrapers/run_all.py --validate   # Validate only (no scraping)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import os
from datetime import date
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scrapers.base import ScrapeItem, deduplicate
from scripts.scrapers.devfolio import scrape_devfolio
from scripts.scrapers.devpost import scrape_devpost
from scripts.scrapers.unstop import scrape_unstop
from scripts.scrapers.internshala import scrape_internshala

OUTPUT_FILE = PROJECT_ROOT / "data" / "scraped_opportunities.json"

SCRAPERS = {
    "devfolio": ("Devfolio", scrape_devfolio),
    "devpost": ("Devpost", scrape_devpost),
    "unstop": ("Unstop", scrape_unstop),
    "internshala": ("Internshala", scrape_internshala),
}


def run_scraper(name: str, func) -> list[ScrapeItem]:
    """Run a single scraper with error handling."""
    logging.info(f"--- Running {name} scraper ---")
    try:
        results = func()
        return results
    except Exception as e:
        logging.error(f"Scraper {name} failed: {e}")
        return []


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


def main():
    parser = argparse.ArgumentParser(description="OPP-Track Scraper Orchestrator")
    parser.add_argument("--devfolio", action="store_true", help="Run only Devfolio scraper")
    parser.add_argument("--devpost", action="store_true", help="Run only Devpost scraper")
    parser.add_argument("--unstop", action="store_true", help="Run only Unstop scraper")
    parser.add_argument("--internshala", action="store_true", help="Run only Internshala scraper")
    parser.add_argument("--validate", action="store_true", help="Validate existing JSON only")
    parser.add_argument("--output", type=str, default=str(OUTPUT_FILE), help="Output JSON path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    output_path = Path(args.output)

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

    # Determine which scrapers to run
    run_all = not (args.devfolio or args.devpost or args.unstop or args.internshala)
    scraper_names = []
    if run_all:
        scraper_names = list(SCRAPERS.keys())
    else:
        if args.devfolio:
            scraper_names.append("devfolio")
        if args.devpost:
            scraper_names.append("devpost")
        if args.unstop:
            scraper_names.append("unstop")
        if args.internshala:
            scraper_names.append("internshala")

    # Run scrapers
    all_items: list[ScrapeItem] = []
    for name in scraper_names:
        label, func = SCRAPERS[name]
        results = run_scraper(name, func)
        all_items.extend(results)
        logging.info(f"{label}: {len(results)} items")

    # Deduplicate
    all_items = deduplicate(all_items)
    logging.info(f"\nTotal unique items: {len(all_items)}")

    # Validate
    valid_items, errors = validate_items(all_items)
    if errors:
        logging.warning(f"\nValidation errors ({len(errors)}):")
        for err in errors:
            logging.warning(f"  {err['title']} ({err['source']}): {', '.join(err['errors'])}")

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = [item.to_dict() for item in valid_items]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logging.info(f"\nSaved {len(valid_items)} items to {output_path}")

    # Print summary by source
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


if __name__ == "__main__":
    main()
