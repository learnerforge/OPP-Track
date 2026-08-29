"""
hackathon.com scraper (BeMyApp / Ideation platform).
The old listing path (/events) now 404s; the live listing pages are e.g.
https://www.hackathon.com/online (upcoming online events) with per-year archives
at /online/<year>. Event cards (.ht-event-card) are server-rendered and expose
title, link, a displayed date, location, description, topics and prize text.
We use StealthyFetcher (headless Chromium) to get past the bot protection and
parse the .ht-event-card elements. The "Showing results N out of N" counter
tells us whether the whole listing was captured.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HACKATHON_COM_URL = "https://www.hackathon.com/online"
HACKATHON_COM_BASE = "https://www.hackathon.com"

PRIZE_RE = re.compile(r"\$\s?[\d,]+(?:\s?[kK])?")

# Matches a "01 Jul" / "16 Sep" style month-day (the cards show a single date
# without a year, e.g. "01 Jul - 12:00 AM").
MONTH_DAY_RE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\b")

ELIGIBILITY_PATTERNS = [
    (re.compile(r"university students\s*\d+\s*years", re.I), "University students"),
    (re.compile(r"university students", re.I), "University students"),
    (re.compile(r"high school", re.I), "High school students"),
    (re.compile(r"students", re.I), "Open to students"),
    (re.compile(r"enterprise developers", re.I), "Open to enterprise developers"),
    (re.compile(r"\d+\s*years of age", re.I), "18+ (per official rules)"),
]

DEFAULT_ELIGIBILITY = "Open to all"


def _extract_eligibility(desc: str) -> str:
    for pattern, label in ELIGIBILITY_PATTERNS:
        if pattern.search(desc):
            return label
    return DEFAULT_ELIGIBILITY


def _extract_prize(desc: str) -> str:
    match = PRIZE_RE.search(desc)
    return match.group(0) if match else ""


def _parse_card(card) -> ScrapeItem | None:
    title_els = card.css(".ht-event-card__title")
    if not title_els:
        return None
    href = title_els[0].attrib.get("href", "")
    title = clean_text(title_els[0].get_all_text())
    if not title or not href:
        return None
    link = urljoin(HACKATHON_COM_BASE, href)

    date_raw = clean_text(
        card.css(".ht-event-card__date")[0].get_all_text() if card.css(".ht-event-card__date") else ""
    )
    # e.g. "01 Jul - 12:00 AM" or "16 Sep - 10:00 AM"
    deadline = ""
    month_day = MONTH_DAY_RE.search(date_raw)
    if month_day:
        deadline = parse_deadline(f"{month_day.group(1)} {month_day.group(2)}")

    location_raw = clean_text(
        card.css(".ht-event-card__location")[0].get_all_text() if card.css(".ht-event-card__location") else ""
    )
    loc_lower = location_raw.lower()
    if any(k in loc_lower for k in ("online", "virtual")):
        location = "Online"
    elif "hybrid" in loc_lower:
        location = "Hybrid"
    else:
        location = "Offline" if location_raw else "Online"

    tags = [clean_text(t.get_all_text()) for t in card.css(".ht-event-topics__tag")]
    tags = [t for t in tags if t] or ["hackathon"]

    desc = clean_text(card.css(".ht-event-card__desc")[0].get_all_text() if card.css(".ht-event-card__desc") else "")
    prize = _extract_prize(desc)
    eligibility = _extract_eligibility(desc)

    notes_parts = ["Source: hackathon.com."]
    if date_raw:
        notes_parts.append(f"Displayed date: {date_raw}.")
    if prize:
        notes_parts.append(f"Prize: {prize}.")

    item = ScrapeItem(
        title=title,
        type="Hackathon",
        source="hackathon.com",
        link=link,
        deadline=deadline,
        eligibility=eligibility,
        tags=tags,
        notes=" ".join(notes_parts),
        location=location,
        prize_pool=prize,
    )
    errors = item.validate()
    if errors:
        logger.debug(f"hackathon.com: skipping invalid item {title}: {errors}")
        return None
    return item


def scrape_hackathon_dotcom() -> list[ScrapeItem]:
    """Scrape upcoming hackathon.com events."""
    logger.info(f"Fetching hackathon.com events: {HACKATHON_COM_URL}")
    try:
        page = StealthyFetcher.fetch(
            HACKATHON_COM_URL,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=60000,
        )
    except Exception as e:
        logger.error(f"hackathon.com fetch failed: {e}")
        return []
    if getattr(page, "status", None) != 200:
        logger.warning(f"hackathon.com returned status {getattr(page, 'status', None)}")
        return []

    cards = page.css(".ht-event-card")
    if not cards:
        logger.warning("hackathon.com: no .ht-event-card elements found")
        return []

    items: list[ScrapeItem] = []
    for card in cards:
        item = _parse_card(card)
        if item:
            items.append(item)
    items = deduplicate_by_link(items)
    logger.info(f"hackathon.com: scraped {len(items)} events")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackathon_dotcom()
    print(f"hackathon.com: {len(results)} items")
    for item in results:
        print(f"  {item.title[:60]} | deadline {item.deadline} | {item.location} | {item.link}")