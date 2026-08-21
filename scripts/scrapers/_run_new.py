"""Run only the new fast scrapers and merge with existing data."""
import sys
import json
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.scrapers.base import ScrapeItem, deduplicate, deduplicate_by_link, quality_score, classify_location

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

OUTPUT_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "scraped_opportunities.json"

# Import all scrapers
from scripts.scrapers.codeforces import scrape_codeforces
from scripts.scrapers.mlh import scrape_mlh
from scripts.scrapers.dorahacks import scrape_dorahacks
from scripts.scrapers.ethglobal import scrape_ethglobal
from scripts.scrapers.kaggle import scrape_kaggle
from scripts.scrapers.analytics_vidhya import scrape_analytics_vidhya
from scripts.scrapers.machinehack import scrape_machinehack
from scripts.scrapers.hackerrank import scrape_hackerrank
from scripts.scrapers.coursera import scrape_coursera
from scripts.scrapers.nptel import scrape_nptel
from scripts.scrapers.swayam import scrape_swayam
from scripts.scrapers.hack2skill import scrape_hack2skill
from scripts.scrapers.techgig import scrape_techgig
from scripts.scrapers.hackindia import scrape_hackindia
from scripts.scrapers.angelhack import scrape_angelhack
from scripts.scrapers.sih import scrape_sih
from scripts.scrapers.tcs_codevita import scrape_tcs_codevita

NEW_SCRAPERS = [
    ("Codeforces", scrape_codeforces),
    ("MLH", scrape_mlh),
    ("DoraHacks", scrape_dorahacks),
    ("ETHGlobal", scrape_ethglobal),
    ("Kaggle", scrape_kaggle),
    ("Analytics Vidhya", scrape_analytics_vidhya),
    ("MachineHack", scrape_machinehack),
    ("HackerRank", scrape_hackerrank),
    ("Coursera", scrape_coursera),
    ("NPTEL", scrape_nptel),
    ("SWAYAM", scrape_swayam),
    ("Hack2Skill", scrape_hack2skill),
    ("TechGig", scrape_techgig),
    ("HackIndia", scrape_hackindia),
    ("AngelHack", scrape_angelhack),
    ("Smart India Hackathon", scrape_sih),
    ("TCS CodeVita", scrape_tcs_codevita),
]

def main():
    # Load existing data
    existing = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        existing = [ScrapeItem(**{k: v for k, v in d.items() if k != "fingerprint"}) for d in data]
        logging.info(f"Loaded {len(existing)} existing items")

    # Run new scrapers
    new_items = []
    for name, func in NEW_SCRAPERS:
        t0 = time.time()
        try:
            items = func()
            elapsed = time.time() - t0
            logging.info(f"{name}: {len(items)} items ({elapsed:.1f}s)")
            new_items.extend(items)
        except Exception as e:
            elapsed = time.time() - t0
            logging.error(f"{name}: FAILED ({elapsed:.1f}s) - {e}")

    logging.info(f"\nNew scrapers produced {len(new_items)} items")

    # Merge
    all_items = existing + new_items
    all_items = deduplicate(all_items)
    logging.info(f"After fingerprint dedup: {len(all_items)} items")
    all_items = deduplicate_by_link(all_items)
    logging.info(f"After link dedup: {len(all_items)} items")

    # Quality score
    for item in all_items:
        item.location = item.location or classify_location(
            f"{item.title} {item.eligibility} {item.notes}"
        )
    scores = [quality_score(item) for item in all_items]
    avg = sum(scores) / len(scores) if scores else 0
    logging.info(f"Quality scores: avg={avg:.1f}, min={min(scores) if scores else 0}, max={max(scores) if scores else 0}")

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump([item.to_dict() for item in all_items], f, indent=2, ensure_ascii=False)

    # Summary
    by_source = {}
    by_type = {}
    for item in all_items:
        by_source[item.source] = by_source.get(item.source, 0) + 1
        by_type[item.type] = by_type.get(item.type, 0) + 1

    logging.info(f"\nBy source ({len(by_source)} sources):")
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        logging.info(f"  {src}: {count}")
    logging.info(f"\nBy type:")
    for t, count in sorted(by_type.items()):
        logging.info(f"  {t}: {count}")

    logging.info(f"\nSaved {len(all_items)} items to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
