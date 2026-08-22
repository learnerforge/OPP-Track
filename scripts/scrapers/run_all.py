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
from scripts.scrapers.buddy4study import scrape_buddy4study
from scripts.scrapers.hackwithinfy import scrape_hackwithinfy
# Phase 2A - Competitive Programming
from scripts.scrapers.atcoder import scrape_atcoder
from scripts.scrapers.codechef import scrape_codechef
from scripts.scrapers.topcoder import scrape_topcoder
from scripts.scrapers.leetcode_contest import scrape_leetcode_contest
from scripts.scrapers.meta_hacker_cup import scrape_meta_hacker_cup
from scripts.scrapers.advent_of_code import scrape_advent_of_code
# Phase 2B - AI/ML Competitions
from scripts.scrapers.aicrowd import scrape_aicrowd
from scripts.scrapers.codabench import scrape_codabench
from scripts.scrapers.zindi import scrape_zindi
from scripts.scrapers.drivendata import scrape_drivendata
from scripts.scrapers.signate import scrape_signate
# Phase 2C - Bug Bounty
from scripts.scrapers.hackerone import scrape_hackerone
from scripts.scrapers.bugcrowd import scrape_bugcrowd
from scripts.scrapers.immunefi import scrape_immunefi
# Phase 2D - Hackathon Platforms
from scripts.scrapers.lablab_ai import scrape_lablab_ai
from scripts.scrapers.hackclub import scrape_hackclub
from scripts.scrapers.hackathon_dotcom import scrape_hackathon_dotcom
from scripts.scrapers.qureka import scrape_qureka
from scripts.scrapers.codegladiators import scrape_codegladiators
# Phase 2E - Certifications
from scripts.scrapers.edx import scrape_edx
from scripts.scrapers.udacity import scrape_udacity
from scripts.scrapers.aws_training import scrape_aws_training
from scripts.scrapers.ibm_skills import scrape_ibm_skills
from scripts.scrapers.google_cloud_skills import scrape_google_cloud_skills
# Phase 4 - Niche Sources
from scripts.scrapers.outreachy import scrape_outreachy
from scripts.scrapers.mlh_fellowship import scrape_mlh_fellowship
from scripts.scrapers.gsoc import scrape_gsoc
from scripts.scrapers.prepbytes import scrape_prepbytes
from scripts.scrapers.interviewbit import scrape_interviewbit
from scripts.scrapers.codingninjas import scrape_codingninjas
from scripts.scrapers.remotive import scrape_remotive
from scripts.scrapers.himalayas import scrape_himalayas
from scripts.scrapers.console_dev import scrape_console_dev
from scripts.scrapers.simplifyjobs import scrape_simplify_internships
from scripts.scrapers.turing import scrape_turing
# Tier 1 - Corporate Careers
from scripts.scrapers.leetcode_problems import scrape_leetcode_problems
from scripts.scrapers.google_careers import scrape_google_careers
from scripts.scrapers.amazon_jobs import scrape_amazon_jobs
from scripts.scrapers.microsoft_careers import scrape_microsoft_careers
from scripts.scrapers.apple_jobs import scrape_apple_jobs
from scripts.scrapers.meta_careers import scrape_meta_careers
from scripts.scrapers.goldman_sachs import scrape_goldman_sachs
from scripts.scrapers.jpmorgan import scrape_jpmorgan
from scripts.scrapers.flipkart import scrape_flipkart
from scripts.scrapers.aiesec import scrape_aiesec
# Tier 2 - Government/Institutional
from scripts.scrapers.nasa_internships import scrape_nasa_internships
from scripts.scrapers.usajobs import scrape_usajobs
from scripts.scrapers.challenge_gov import scrape_challenge_gov
from scripts.scrapers.nsf_reu import scrape_nsf_reu
from scripts.scrapers.cern_internships import scrape_cern_internships
from scripts.scrapers.mitacs import scrape_mitacs
from scripts.scrapers.daad_rise import scrape_daad_rise
# Tier 3 - Job Aggregators & Scholarships
from scripts.scrapers.linkedin_jobs import scrape_linkedin_jobs
from scripts.scrapers.indeed import scrape_indeed
from scripts.scrapers.wellfound import scrape_wellfound
from scripts.scrapers.yc_jobs import scrape_yc_jobs
from scripts.scrapers.handshake import scrape_handshake
from scripts.scrapers.forage import scrape_forage
from scripts.scrapers.virtual_internships import scrape_virtual_internships
from scripts.scrapers.fastweb import scrape_fastweb
from scripts.scrapers.scholarshipowl import scrape_scholarshipowl
from scripts.scrapers.reskilll import scrape_reskilll

OUTPUT_FILE = PROJECT_ROOT / "data" / "scraped_opportunities.json"
SOURCES_FILE = PROJECT_ROOT / "scripts" / "scrapers" / "sources.json"
ENRICH_THRESHOLD = 50

SCRAPERS = {
    "devfolio": ("Devfolio", scrape_devfolio),
    "devpost": ("Devpost", scrape_devpost),
    "unstop": ("Unstop", scrape_unstop),
    "hackerearth": ("HackerEarth", scrape_hackerearth),
    "internshala": ("Internshala", scrape_internshala),
    "codeforces": ("Codeforces", scrape_codeforces),
    "mlh": ("MLH", scrape_mlh),
    "dorahacks": ("DoraHacks", scrape_dorahacks),
    "ethglobal": ("ETHGlobal", scrape_ethglobal),
    "kaggle": ("Kaggle", scrape_kaggle),
    "analytics_vidhya": ("Analytics Vidhya", scrape_analytics_vidhya),
    "machinehack": ("MachineHack", scrape_machinehack),
    "hackerrank": ("HackerRank", scrape_hackerrank),
    "coursera": ("Coursera", scrape_coursera),
    "nptel": ("NPTEL", scrape_nptel),
    "swayam": ("SWAYAM", scrape_swayam),
    "hack2skill": ("Hack2Skill", scrape_hack2skill),
    "techgig": ("TechGig", scrape_techgig),
    "hackindia": ("HackIndia", scrape_hackindia),
    "angelhack": ("AngelHack", scrape_angelhack),
    "sih": ("Smart India Hackathon", scrape_sih),
    "tcs_codevita": ("TCS CodeVita", scrape_tcs_codevita),
    "buddy4study": ("Buddy4Study", scrape_buddy4study),
    "hackwithinfy": ("HackWithInfy", scrape_hackwithinfy),
    # Phase 2A - Competitive Programming
    "atcoder": ("AtCoder", scrape_atcoder),
    "codechef": ("CodeChef", scrape_codechef),
    "topcoder": ("Topcoder", scrape_topcoder),
    "leetcode_contest": ("LeetCode Contests", scrape_leetcode_contest),
    "meta_hacker_cup": ("Meta Hacker Cup", scrape_meta_hacker_cup),
    "advent_of_code": ("Advent of Code", scrape_advent_of_code),
    # Phase 2B - AI/ML Competitions
    "aicrowd": ("AIcrowd", scrape_aicrowd),
    "codabench": ("CodaBench", scrape_codabench),
    "zindi": ("Zindi", scrape_zindi),
    "drivendata": ("DrivenData", scrape_drivendata),
    "signate": ("SIGNATE", scrape_signate),
    # Phase 2C - Bug Bounty
    "hackerone": ("HackerOne", scrape_hackerone),
    "bugcrowd": ("Bugcrowd", scrape_bugcrowd),
    "immunefi": ("Immunefi", scrape_immunefi),
    # Phase 2D - Hackathon Platforms
    "lablab_ai": ("lablab.ai", scrape_lablab_ai),
    "hackclub": ("Hack Club", scrape_hackclub),
    "hackathon_dotcom": ("Hackathon.com", scrape_hackathon_dotcom),
    "qureka": ("Qureka", scrape_qureka),
    "codegladiators": ("CodeGladiators", scrape_codegladiators),
    # Phase 2E - Certifications
    "edx": ("edX", scrape_edx),
    "udacity": ("Udacity", scrape_udacity),
    "aws_training": ("AWS Training", scrape_aws_training),
    "ibm_skills": ("IBM Skills", scrape_ibm_skills),
    "google_cloud_skills": ("Google Cloud Skills", scrape_google_cloud_skills),
    # Phase 4 - Niche Sources
    "outreachy": ("Outreachy", scrape_outreachy),
    "mlh_fellowship": ("MLH Fellowship", scrape_mlh_fellowship),
    "gsoc": ("Google Summer of Code", scrape_gsoc),
    "prepbytes": ("PrepBytes", scrape_prepbytes),
    "interviewbit": ("InterviewBit", scrape_interviewbit),
    "codingninjas": ("CodingNinjas", scrape_codingninjas),
    "remotive": ("Remotive", scrape_remotive),
    "himalayas": ("Himalayas", scrape_himalayas),
    "console_dev": ("Console.dev", scrape_console_dev),
    "simplifyjobs": ("SimplifyJobs", scrape_simplify_internships),
    "turing": ("Turing", scrape_turing),
    # Tier 1 - Corporate Careers
    "leetcode_problems": ("LeetCode Problems", scrape_leetcode_problems),
    "google_careers": ("Google Careers", scrape_google_careers),
    "amazon_jobs": ("Amazon Jobs", scrape_amazon_jobs),
    "microsoft_careers": ("Microsoft Careers", scrape_microsoft_careers),
    "apple_jobs": ("Apple Jobs", scrape_apple_jobs),
    "meta_careers": ("Meta Careers", scrape_meta_careers),
    "goldman_sachs": ("Goldman Sachs", scrape_goldman_sachs),
    "jpmorgan": ("JPMorgan", scrape_jpmorgan),
    "flipkart": ("Flipkart", scrape_flipkart),
    "aiesec": ("AIESEC", scrape_aiesec),
    # Tier 2 - Government/Institutional
    "nasa_internships": ("NASA Internships", scrape_nasa_internships),
    "usajobs": ("USAJobs", scrape_usajobs),
    "challenge_gov": ("Challenge.gov", scrape_challenge_gov),
    "nsf_reu": ("NSF REU", scrape_nsf_reu),
    "cern_internships": ("CERN Internships", scrape_cern_internships),
    "mitacs": ("Mitacs", scrape_mitacs),
    "daad_rise": ("DAAD RISE", scrape_daad_rise),
    # Tier 3 - Job Aggregators & Scholarships
    "linkedin_jobs": ("LinkedIn Jobs", scrape_linkedin_jobs),
    "indeed": ("Indeed", scrape_indeed),
    "wellfound": ("Wellfound", scrape_wellfound),
    "yc_jobs": ("YC Jobs", scrape_yc_jobs),
    "handshake": ("Handshake", scrape_handshake),
    "forage": ("Forage", scrape_forage),
    "virtual_internships": ("Virtual Internships", scrape_virtual_internships),
    "fastweb": ("Fastweb", scrape_fastweb),
    "scholarshipowl": ("ScholarshipOwl", scrape_scholarshipowl),
    "reskilll": ("Reskilll", scrape_reskilll),
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
        results = scrape_source(source_config)
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
