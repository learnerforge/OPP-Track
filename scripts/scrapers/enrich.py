"""
enrich.py — Tier-2 detail page scraper.

Visits individual event pages to fill in missing data (deadline, location,
prize, eligibility, participants) for items with quality_score < 50.

Usage:
    python scripts/scrapers/enrich.py              # Enrich low-quality items
    python scripts/scrapers/enrich.py --dry-run    # Preview without changes
    python scripts/scrapers/enrich.py --threshold 70  # Enrich below score 70
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
import sys
from pathlib import Path
from urllib.parse import urlparse

from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import (
    ScrapeItem,
    parse_deadline,
    clean_text,
    classify_location,
    quality_score,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "scraped_opportunities.json"

# Delay between requests to avoid rate-limiting
REQUEST_DELAY = 2.0


# ── Source detection ─────────────────────────────────────────────────


def _detect_source(link: str) -> str:
    """Detect the platform from the item's URL."""
    host = urlparse(link).hostname or ""
    if "devfolio.co" in host:
        return "devfolio"
    if "devpost.com" in host:
        return "devpost"
    if "hackerearth.com" in host:
        return "hackerearth"
    return "unknown"


# ── Devfolio detail page extraction ─────────────────────────────────


def _extract_devfolio(page, item: dict) -> dict:
    """Extract enrichment data from a Devfolio detail page."""
    updates: dict = {}
    page_text = page.get_all_text() if hasattr(page, "get_all_text") else ""
    if not page_text:
        page_text = clean_text(str(page.html_content)) if hasattr(page, "html_content") else ""

    page_lower = page_text.lower()

    # ── Deadline ──────────────────────────────────────────────────
    if not item.get("deadline"):
        # Devfolio pages often show "Application Deadline" or "Submissions Due"
        deadline_patterns = [
            r'(?:deadline|due|closes?|ends?)\s*(?:on|:)?\s*(\w+\s+\d{1,2},?\s*\d{4})',
            r'(\w+\s+\d{1,2},?\s*\d{4})\s*(?:\||\n|$)',
            r'(\d{1,2})/(\d{1,2})/(\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                raw = match.group(0) if not match.groups() else match.group(1)
                parsed = parse_deadline(raw)
                if parsed:
                    updates["deadline"] = parsed
                    break

    # ── Location ──────────────────────────────────────────────────
    if not item.get("location"):
        if "online" in page_lower and ("offline" in page_lower or "in-person" in page_lower or "on-site" in page_lower):
            updates["location"] = "Hybrid"
        elif "offline" in page_lower or "in-person" in page_lower or "on-site" in page_lower:
            updates["location"] = "Offline"
        elif "online" in page_lower or "virtual" in page_lower or "remote" in page_lower:
            updates["location"] = "Online"

    # ── Prize pool ────────────────────────────────────────────────
    if not item.get("prize_pool") or item.get("prize_pool") in ("$", "€", "₹", ""):
        prize_match = re.search(
            r'(?:prize|pool|total|worth|worth\s+of)\s*(?:pool|:)?\s*\$\s*([\d,]+(?:\.\d+)?)',
            page_text, re.IGNORECASE,
        )
        if not prize_match:
            prize_match = re.search(
                r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:in\s+)?prize',
                page_text, re.IGNORECASE,
            )
        if not prize_match:
            prize_match = re.search(
                r'(?:prize|pool|total)\s*(?:pool)?\s*(?:worth|:)?\s*([\d,]+(?:\.\d+)?)\s*(?:usd|\$)',
                page_text, re.IGNORECASE,
            )
        if prize_match:
            updates["prize_pool"] = f"${prize_match.group(1)}"

    # ── Eligibility ───────────────────────────────────────────────
    eligibility_parts = []
    if "student" in page_lower:
        eligibility_parts.append("Students")
    if "open to all" in page_lower or "everyone" in page_lower:
        eligibility_parts.append("Open to all")
    if "18" in page_lower and ("year" in page_lower or "age" in page_lower):
        eligibility_parts.append("18+")
    if "India" in page_text or "indian" in page_lower:
        eligibility_parts.append("India-focused")
    if eligibility_parts:
        updates["eligibility"] = ", ".join(eligibility_parts)

    # ── Participants ──────────────────────────────────────────────
    if not item.get("participants") or item.get("participants") in ("0", ""):
        part_match = re.search(r'([\d,]+)\s*(?:\+?\s*)?(?:teams?|participants?|registr)', page_text, re.IGNORECASE)
        if part_match:
            updates["participants"] = part_match.group(1)

    return updates


# ── Devpost detail page extraction ──────────────────────────────────


def _extract_devpost(page, item: dict) -> dict:
    """Extract enrichment data from a Devpost detail page."""
    updates: dict = {}
    page_text = page.get_all_text() if hasattr(page, "get_all_text") else ""
    if not page_text:
        page_text = clean_text(str(page.html_content)) if hasattr(page, "html_content") else ""

    page_lower = page_text.lower()

    # ── Deadline ──────────────────────────────────────────────────
    if not item.get("deadline"):
        # Devpost shows "Submission Period: Aug 29 – Sep 01, 2026"
        deadline_patterns = [
            r'(?:submission\s+period|deadline|due|ends?|closes?)\s*(?:on|:)?\s*(\w+\s+\d{1,2},?\s*\d{4})',
            r'(?:to|through|until)\s+(\w+\s+\d{1,2},?\s*\d{4})',
            r'(\w+\s+\d{1,2})\s*[-–]\s*(\w+\s+\d{1,2},?\s*\d{4})',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                # For date ranges, take the last date (end of submission)
                raw = match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(1)
                parsed = parse_deadline(raw)
                if parsed:
                    updates["deadline"] = parsed
                    break

    # ── Location ──────────────────────────────────────────────────
    if not item.get("location"):
        loc_match = re.search(
            r'(?:location|format|mode)\s*(?::)?\s*(Online|Offline|Hybrid|In[- ]?Person)',
            page_text, re.IGNORECASE,
        )
        if loc_match:
            updates["location"] = classify_location(loc_match.group(1))
        else:
            updates["location"] = classify_location(page_text[:2000])

    # ── Prize ─────────────────────────────────────────────────────
    if not item.get("prize_pool") or item.get("prize_pool") in ("$", "€", "₹", ""):
        # Look for total prize pool
        prize_patterns = [
            r'(?:total|grand|prize\s*pool|worth)\s*(?:prize\s*)?(?:pool)?\s*(?:worth)?\s*\$\s*([\d,]+(?:\.\d+)?)',
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:in\s+)?(?:prize|awards?|total)',
            r'([\d,]+)\s*(?:in\s+)?(?:prize|awards?|total)\s*(?:money)?',
        ]
        for pattern in prize_patterns:
            prize_match = re.search(pattern, page_text, re.IGNORECASE)
            if prize_match:
                amount = prize_match.group(1).replace(",", "")
                if amount.replace(".", "").isdigit() and float(amount) > 0:
                    updates["prize_pool"] = f"${prize_match.group(1)}"
                    break

    # ── Eligibility ───────────────────────────────────────────────
    eligibility_parts = []
    if "student" in page_lower:
        eligibility_parts.append("Students")
    if "open to all" in page_lower or "everyone" in page_lower or "anyone" in page_lower:
        eligibility_parts.append("Open to all")
    if "18" in page_lower and ("year" in page_lower or "age" in page_lower):
        eligibility_parts.append("18+")
    if "developer" in page_lower and "student" not in page_lower:
        eligibility_parts.append("Developers")
    if eligibility_parts:
        updates["eligibility"] = ", ".join(eligibility_parts)

    # ── Participants ──────────────────────────────────────────────
    if not item.get("participants") or item.get("participants") in ("0", ""):
        part_match = re.search(r'([\d,]+)\s*(?:\+?\s*)?(?:teams?|participants?|registr)', page_text, re.IGNORECASE)
        if part_match:
            updates["participants"] = part_match.group(1)

    return updates


# ── HackerEarth detail page extraction ──────────────────────────────


def _extract_hackerearth(page, item: dict) -> dict:
    """Extract enrichment data from a HackerEarth detail page."""
    updates: dict = {}
    page_text = page.get_all_text() if hasattr(page, "get_all_text") else ""
    if not page_text:
        page_text = clean_text(str(page.html_content)) if hasattr(page, "html_content") else ""

    page_lower = page_text.lower()

    # ── Deadline ──────────────────────────────────────────────────
    if not item.get("deadline"):
        deadline_patterns = [
            r'(?:deadline|ends?|closes?|due|submission\s+deadline)\s*(?:on|:)?\s*(\w+\s+\d{1,2},?\s*\d{4})',
            r'(\w+\s+\d{1,2},?\s*\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                parsed = parse_deadline(match.group(1))
                if parsed:
                    updates["deadline"] = parsed
                    break

    # ── Prize ─────────────────────────────────────────────────────
    if not item.get("prize_pool") or item.get("prize_pool") in ("$", "€", "₹", ""):
        prize_patterns = [
            r'(?:prize|pool|total|worth)\s*(?:pool)?\s*(?:worth)?\s*\$\s*([\d,]+(?:\.\d+)?)',
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:in\s+)?(?:prize|awards?|total)',
            r'(?:prize|reward)\s*(?:worth)?\s*(?:INR|₹)\s*([\d,]+(?:\.\d+)?)',
            r'(?:INR|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:in\s+)?(?:prize|awards?)',
        ]
        for pattern in prize_patterns:
            prize_match = re.search(pattern, page_text, re.IGNORECASE)
            if prize_match:
                amount = prize_match.group(1).replace(",", "")
                if amount.replace(".", "").isdigit() and float(amount) > 0:
                    prefix = "₹" if "INR" in pattern or "₹" in pattern else "$"
                    updates["prize_pool"] = f"{prefix}{prize_match.group(1)}"
                    break

    # ── Participants ──────────────────────────────────────────────
    if not item.get("participants") or item.get("participants") in ("0", ""):
        part_match = re.search(r'([\d,]+\.?\d*[Kk]?)\s*(?:\+?\s*)?(?:teams?|participants?|registr)', page_text, re.IGNORECASE)
        if part_match:
            updates["participants"] = part_match.group(1)

    # ── Eligibility ───────────────────────────────────────────────
    eligibility_parts = []
    if "student" in page_lower:
        eligibility_parts.append("Students")
    if "open to all" in page_lower or "everyone" in page_lower:
        eligibility_parts.append("Open to all")
    if "developer" in page_lower:
        eligibility_parts.append("Developers")
    if eligibility_parts:
        updates["eligibility"] = ", ".join(eligibility_parts)

    return updates


# ── Main enrichment pipeline ────────────────────────────────────────


def _fetch_detail_page(link: str):
    """Fetch a detail page with StealthyFetcher. Returns page object or None."""
    try:
        page = StealthyFetcher.fetch(
            link,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=30000,
        )
        if page.status != 200:
            logger.warning(f"  HTTP {page.status} for {link}")
            return None
        return page
    except Exception as e:
        logger.error(f"  Fetch error for {link}: {e}")
        return None


def _needs_enrichment(item: dict, threshold: int) -> bool:
    """Check whether an item falls below the quality-score threshold."""
    sc = ScrapeItem(
        title=item.get("title", ""),
        type=item.get("type", ""),
        source=item.get("source", ""),
        link=item.get("link", ""),
        deadline=item.get("deadline", ""),
        eligibility=item.get("eligibility", ""),
        tags=item.get("tags", []),
        notes=item.get("notes", ""),
        location=item.get("location", ""),
        prize_pool=item.get("prize_pool", ""),
        participants=item.get("participants", ""),
        organizer=item.get("organizer", ""),
        duration=item.get("duration", ""),
    )
    return quality_score(sc) < threshold


def enrich_items(dry_run: bool = False, threshold: int = 50) -> None:
    """Main enrichment pipeline.

    1. Load scraped_opportunities.json
    2. Identify items below the quality threshold
    3. Visit each detail page and extract missing fields
    4. Update the item (or preview in dry-run mode)
    5. Write back to disk
    """
    if not DATA_FILE.exists():
        logger.error(f"Data file not found: {DATA_FILE}")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    logger.info(f"Loaded {len(items)} items from {DATA_FILE}")

    # Filter to items needing enrichment
    candidates = [
        (i, item) for i, item in enumerate(items)
        if _needs_enrichment(item, threshold)
    ]
    logger.info(f"Found {len(candidates)} items below quality threshold ({threshold})")

    if not candidates:
        logger.info("Nothing to enrich.")
        return

    enriched_count = 0
    failed_count = 0
    skipped_count = 0

    for idx, (pos, item) in enumerate(candidates):
        title = item.get("title", "?")
        link = item.get("link", "")
        source = _detect_source(link)

        logger.info(
            f"[{idx + 1}/{len(candidates)}] Enriching: {title} "
            f"(source={source}, score={quality_score(ScrapeItem(**{k: v for k, v in item.items() if k != 'fingerprint'}))})"
        )

        if source == "unknown" or not link:
            logger.warning(f"  Skipping — cannot determine source for link: {link}")
            skipped_count += 1
            continue

        # Rate limit
        if idx > 0:
            time.sleep(REQUEST_DELAY)

        page = _fetch_detail_page(link)
        if page is None:
            failed_count += 1
            continue

        # Dispatch to source-specific extractor
        extractor = {
            "devfolio": _extract_devfolio,
            "devpost": _extract_devpost,
            "hackerearth": _extract_hackerearth,
        }.get(source)

        if extractor is None:
            logger.warning(f"  No extractor for source: {source}")
            skipped_count += 1
            continue

        updates = extractor(page, item)

        if not updates:
            logger.info(f"  No new data found for: {title}")
            continue

        # Log what we found
        for field, value in updates.items():
            old = item.get(field, "")
            logger.info(f"  {field}: {old!r} -> {value!r}")

        if dry_run:
            logger.info(f"  [DRY RUN] Would update {len(updates)} field(s)")
        else:
            for field, value in updates.items():
                item[field] = value
            enriched_count += 1
            logger.info(f"  Updated {len(updates)} field(s)")

    # Summary
    logger.info("\n─── Enrichment Summary ───")
    logger.info(f"  Total candidates: {len(candidates)}")
    logger.info(f"  Enriched:         {enriched_count}")
    logger.info(f"  Failed:           {failed_count}")
    logger.info(f"  Skipped:          {skipped_count}")

    if dry_run:
        logger.info("\n[DRY RUN] No changes written to disk.")
        return

    # Write back
    if enriched_count > 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        logger.info(f"\nSaved enriched data to {DATA_FILE}")
    else:
        logger.info("\nNo items were enriched — file unchanged.")


def main():
    parser = argparse.ArgumentParser(
        description="Enrich low-quality scraped items by visiting detail pages"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be enriched without making changes",
    )
    parser.add_argument(
        "--threshold", type=int, default=50,
        help="Quality score threshold — items below this are enriched (default: 50)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose (DEBUG) logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    enrich_items(dry_run=args.dry_run, threshold=args.threshold)


if __name__ == "__main__":
    main()
