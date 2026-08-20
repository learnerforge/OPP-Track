"""
enrich.py — Tier-2 detail page scraper — ENHANCED.
Adds Internshala support, improves Devfolio JSON extraction, better all extractors.

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
    if "internshala.com" in host:
        return "internshala"
    if "unstop.com" in host:
        return "unstop"
    return "unknown"


# ── Internshala detail page extraction ──────────────────────────────


def _extract_internshala(page, item: dict) -> dict:
    """Extract enrichment data from an Internshala detail page."""
    updates: dict = {}
    body = str(page.body) if page.body else ""
    body_text = re.sub(r'<[^>]+>', ' ', body)
    body_text = re.sub(r'\s+', ' ', body_text).strip()
    body_lower = body_text.lower()

    # Deadline
    if not item.get("deadline"):
        deadline_patterns = [
            r'(?:deadline|last\s+date\s+to\s+apply|apply\s+by)[:\s]*(\w+\s+\d{1,2},?\s*\d{4})',
            r'(\w+\s+\d{1,2},?\s*\d{4})\s*(?:\||\n|$)',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                parsed = parse_deadline(match.group(1))
                if parsed:
                    updates["deadline"] = parsed
                    break

    # Duration
    if not item.get("duration"):
        dur_match = re.search(r'(\d+)\s*(month|week|day)s?', body_lower)
        if dur_match:
            updates["duration"] = dur_match.group(0).title()

    # Eligibility
    elig_parts = []
    if "student" in body_lower:
        elig_parts.append("Students")
    if "who can apply" in body_lower:
        # Try to extract the actual eligibility text
        elig_match = re.search(r'who\s+can\s+apply[:\s]*([^.]*(?:student|graduate|fresher|bachelor|master|degree)[^.]*)', body_text, re.IGNORECASE)
        if elig_match:
            elig_text = elig_match.group(1).strip()[:200]
            if len(elig_text) > 10:
                elig_parts.append(elig_text[:100])
    if "fresher" in body_lower:
        elig_parts.append("Freshers welcome")
    if elig_parts:
        updates["eligibility"] = ", ".join(elig_parts)

    # Organizer
    if not item.get("organizer"):
        org_match = re.search(r'at\s+([\w\s&]+?)(?:\s*[-–|]|$)', body_text[:500])
        if org_match:
            org = org_match.group(1).strip()
            if 2 < len(org) < 60:
                updates["organizer"] = org

    # Location
    if not item.get("location"):
        loc_match = re.search(r'(?:location|city)[:\s]*(\w[\w\s,]+?)(?:\s*[-–|.]|$)', body_text[:1000], re.IGNORECASE)
        if loc_match:
            updates["location"] = classify_location(loc_match.group(1).strip())

    return updates


# ── Devfolio detail page extraction ─────────────────────────────────


def _extract_devfolio(page, item: dict) -> dict:
    """Extract enrichment data from a Devfolio detail page using JSON payload."""
    updates: dict = {}
    body = str(page.body) if page.body else ""
    body_text = re.sub(r'<[^>]+>', ' ', body)
    body_text = re.sub(r'\s+', ' ', body_text).strip()
    body_lower = body_text.lower()

    # Try to extract JSON payload
    try:
        # Look for dehydratedState or hackathon JSON
        json_match = re.search(r'"dehydratedState":\s*(\{.*?\})\s*,\s*"(?:moreHackathons|hackathon_partnership|judges")', body, re.DOTALL)
        if json_match:
            json_data = json.loads(json_match.group(1))
            queries = json_data.get("queries", [])
            for query in queries:
                state = query.get("state", {})
                data = state.get("data", {})
                hackathon = data.get("hackathon", {})
                if hackathon:
                    # Themes/tags
                    themes = hackathon.get("themes", [])
                    if themes:
                        tag_names = [t.get("theme", {}).get("name", "") for t in themes if t.get("theme", {}).get("name")]
                        if tag_names and tag_names != ["No Restrictions"]:
                            updates["tags"] = tag_names

                    # Prize
                    prize_details = hackathon.get("prizeDetails", [])
                    if prize_details:
                        total = 0
                        currency = ""
                        for track in prize_details:
                            for prize in track.get("prizes", []):
                                amt = prize.get("amount", 0)
                                if amt:
                                    total += amt
                                    currency = prize.get("currency", "USD")
                        if total > 0:
                            symbol = "$" if currency == "USD" else "₹" if currency == "INR" else currency + " "
                            updates["prize_pool"] = f"{symbol}{total:,}"

                    # Organizer
                    organizer = hackathon.get("organizer", {})
                    if organizer and isinstance(organizer, dict):
                        org_name = organizer.get("name", "")
                        if org_name:
                            updates["organizer"] = org_name

                    # Participants
                    participants = hackathon.get("participants_count")
                    if participants:
                        updates["participants"] = str(participants)

                    # Online/offline
                    online = hackathon.get("online")
                    if online is True:
                        updates["location"] = "Online"
                    elif online is False:
                        city = hackathon.get("city", "")
                        country = hackathon.get("country", "")
                        if city or country:
                            updates["location"] = f"{city}, {country}" if city else country

                    # Dates
                    starts_at = hackathon.get("starts_at", "")
                    if starts_at:
                        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', starts_at)
                        if date_match and not item.get("deadline"):
                            updates["deadline"] = date_match.group(1)
                    break
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.debug(f"  JSON parse error: {e}")

    # Fallback: HTML-based extraction
    if not updates.get("deadline"):
        deadline_match = re.search(r'(\d{4}-\d{2}-\d{2})', body)
        if deadline_match:
            updates["deadline"] = deadline_match.group(1)

    if not updates.get("tags"):
        tag_matches = re.findall(r'"name":"([^"]+)".*?"theme":\{"name":"([^"]+)"\}', body)
        if tag_matches:
            tags = list(set(t[1] for t in tag_matches if t[1] != "No Restrictions"))
            if tags:
                updates["tags"] = tags[:5]

    # Eligibility
    elig_parts = []
    if "student" in body_lower:
        elig_parts.append("Students")
    if "open to all" in body_lower or "everyone" in body_lower:
        elig_parts.append("Open to all")
    if "developer" in body_lower:
        elig_parts.append("Developers")
    if elig_parts:
        updates["eligibility"] = ", ".join(elig_parts)

    # Participants fallback
    if not updates.get("participants"):
        part_match = re.search(r'([\d,]+)\s*(?:\+?\s*)?(?:teams?|participants?|registr)', body_text, re.IGNORECASE)
        if part_match:
            updates["participants"] = part_match.group(1)

    return updates


# ── Devpost detail page extraction ──────────────────────────────────


def _extract_devpost(page, item: dict) -> dict:
    """Extract enrichment data from a Devpost detail page."""
    updates: dict = {}
    body = str(page.body) if page.body else ""
    body_text = re.sub(r'<[^>]+>', ' ', body)
    body_text = re.sub(r'\s+', ' ', body_text).strip()
    body_lower = body_text.lower()

    # Deadline
    if not item.get("deadline"):
        deadline_patterns = [
            r'(?:submission\s+period|deadline|due|ends?|closes?)\s*(?:on|:)?\s*(\w+\s+\d{1,2},?\s*\d{4})',
            r'(?:to|through|until)\s+(\w+\s+\d{1,2},?\s*\d{4})',
            r'(\w+\s+\d{1,2})\s*[-–]\s*(\w+\s+\d{1,2},?\s*\d{4})',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                raw = match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(1)
                parsed = parse_deadline(raw)
                if parsed:
                    updates["deadline"] = parsed
                    break

    # Location
    if not item.get("location"):
        loc_match = re.search(
            r'(?:location|format|mode)\s*(?::)?\s*(Online|Offline|Hybrid|In[- ]?Person)',
            body_text, re.IGNORECASE,
        )
        if loc_match:
            updates["location"] = classify_location(loc_match.group(1))
        else:
            updates["location"] = classify_location(body_text[:2000])

    # Prize
    if not item.get("prize_pool") or item.get("prize_pool") in ("$", "€", "₹", ""):
        prize_patterns = [
            r'(?:total|grand|prize\s*pool|worth)\s*(?:prize\s*)?(?:pool)?\s*(?:worth)?\s*\$\s*([\d,]+(?:\.\d+)?)',
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:in\s+)?(?:prize|awards?|total)',
        ]
        for pattern in prize_patterns:
            prize_match = re.search(pattern, body_text, re.IGNORECASE)
            if prize_match:
                amount = prize_match.group(1).replace(",", "")
                if amount.replace(".", "").isdigit() and float(amount) > 0:
                    updates["prize_pool"] = f"${prize_match.group(1)}"
                    break

    # Eligibility
    elig_parts = []
    if "student" in body_lower:
        elig_parts.append("Students")
    if "open to all" in body_lower or "everyone" in body_lower or "anyone" in body_lower:
        elig_parts.append("Open to all")
    if "developer" in body_lower and "student" not in body_lower:
        elig_parts.append("Developers")
    if "designer" in body_lower:
        elig_parts.append("Designers")
    if "beginner" in body_lower:
        elig_parts.append("Beginners welcome")
    if elig_parts:
        updates["eligibility"] = ", ".join(elig_parts)

    # Participants
    if not item.get("participants"):
        part_match = re.search(r'([\d,]+)\s*(?:\+?\s*)?(?:teams?|participants?|registr)', body_text, re.IGNORECASE)
        if part_match:
            updates["participants"] = part_match.group(1)

    return updates


# ── HackerEarth detail page extraction ──────────────────────────────


def _extract_hackerearth(page, item: dict) -> dict:
    """Extract enrichment data from a HackerEarth detail page."""
    updates: dict = {}
    body = str(page.body) if page.body else ""
    body_text = re.sub(r'<[^>]+>', ' ', body)
    body_text = re.sub(r'\s+', ' ', body_text).strip()
    body_lower = body_text.lower()

    # Deadline
    if not item.get("deadline"):
        deadline_patterns = [
            r'(?:deadline|ends?|closes?|due|submission\s+deadline)\s*(?:on|:)?\s*(\w+\s+\d{1,2},?\s*\d{4})',
            r'(\w+\s+\d{1,2},?\s*\d{4})',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                parsed = parse_deadline(match.group(1))
                if parsed:
                    updates["deadline"] = parsed
                    break

    # Prize
    if not item.get("prize_pool") or item.get("prize_pool") in ("$", "€", "₹", ""):
        prize_patterns = [
            r'(?:prize|pool|total|worth)\s*(?:pool)?\s*(?:worth)?\s*\$\s*([\d,]+(?:\.\d+)?)',
            r'(?:prize|reward)\s*(?:worth)?\s*(?:INR|₹)\s*([\d,]+(?:\.\d+)?)',
        ]
        for pattern in prize_patterns:
            prize_match = re.search(pattern, body_text, re.IGNORECASE)
            if prize_match:
                amount = prize_match.group(1).replace(",", "")
                if amount.replace(".", "").isdigit() and float(amount) > 0:
                    prefix = "₹" if "INR" in pattern or "₹" in pattern else "$"
                    updates["prize_pool"] = f"{prefix}{prize_match.group(1)}"
                    break

    # Participants
    if not item.get("participants"):
        part_match = re.search(r'([\d,]+\.?\d*[Kk]?)\s*(?:\+?\s*)?(?:teams?|participants?|registr)', body_text, re.IGNORECASE)
        if part_match:
            updates["participants"] = part_match.group(1)

    # Tags from themes
    if not item.get("tags"):
        theme_matches = re.findall(r'(?:theme|tag|category)[:\s]*([A-Z][\w\s/&]+)', body_text[:2000])
        if theme_matches:
            updates["tags"] = list(set(t.strip() for t in theme_matches if len(t.strip()) < 30))[:5]

    # Eligibility
    elig_parts = []
    if "student" in body_lower:
        elig_parts.append("Students")
    if "open to all" in body_lower or "everyone" in body_lower:
        elig_parts.append("Open to all")
    if "developer" in body_lower:
        elig_parts.append("Developers")
    if elig_parts:
        updates["eligibility"] = ", ".join(elig_parts)

    return updates


# ── Unstop detail page extraction ───────────────────────────────────


def _extract_unstop(page, item: dict) -> dict:
    """Extract enrichment data from an Unstop detail page."""
    updates: dict = {}
    body = str(page.body) if page.body else ""
    body_text = re.sub(r'<[^>]+>', ' ', body)
    body_text = re.sub(r'\s+', ' ', body_text).strip()
    body_lower = body_text.lower()

    # Deadline
    if not item.get("deadline"):
        deadline_patterns = [
            r'(?:deadline|last\s+date|apply\s+by|registration\s+ends?)[:\s]*(\w+\s+\d{1,2},?\s*\d{4})',
            r'(\w+\s+\d{1,2},?\s*\d{4})',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                parsed = parse_deadline(match.group(1))
                if parsed:
                    updates["deadline"] = parsed
                    break

    # Eligibility
    elig_parts = []
    if "student" in body_lower:
        elig_parts.append("Students")
    if "open to all" in body_lower or "everyone" in body_lower:
        elig_parts.append("Open to all")
    if "college" in body_lower or "university" in body_lower:
        elig_parts.append("College students")
    if "professional" in body_lower:
        elig_parts.append("Professionals")
    if elig_parts:
        updates["eligibility"] = ", ".join(elig_parts)

    # Organizer
    if not item.get("organizer"):
        org_match = re.search(r'(?:organized|hosted|by)\s+(?:by)?\s*([\w\s&]+?)(?:\s*[-–|.]|$)', body_text[:1000], re.IGNORECASE)
        if org_match:
            org = org_match.group(1).strip()
            if 2 < len(org) < 60:
                updates["organizer"] = org

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
    """Main enrichment pipeline."""
    if not DATA_FILE.exists():
        logger.error(f"Data file not found: {DATA_FILE}")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    logger.info(f"Loaded {len(items)} items from {DATA_FILE}")

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

        if idx > 0:
            time.sleep(REQUEST_DELAY)

        page = _fetch_detail_page(link)
        if page is None:
            failed_count += 1
            continue

        extractor = {
            "devfolio": _extract_devfolio,
            "devpost": _extract_devpost,
            "hackerearth": _extract_hackerearth,
            "internshala": _extract_internshala,
            "unstop": _extract_unstop,
        }.get(source)

        if extractor is None:
            logger.warning(f"  No extractor for source: {source}")
            skipped_count += 1
            continue

        updates = extractor(page, item)

        if not updates:
            logger.info(f"  No new data found for: {title}")
            continue

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

    logger.info("\n─── Enrichment Summary ───")
    logger.info(f"  Total candidates: {len(candidates)}")
    logger.info(f"  Enriched:         {enriched_count}")
    logger.info(f"  Failed:           {failed_count}")
    logger.info(f"  Skipped:          {skipped_count}")

    if dry_run:
        logger.info("\n[DRY RUN] No changes written to disk.")
        return

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
