"""
Devfolio hackathon scraper.
Devfolio is a Next.js SPA — uses StealthyFetcher for JS rendering.
Extracts titles, links, dates, and themes using positional matching.
"""

from __future__ import annotations

import re
import logging
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

DEVFOLIO_BASE = "https://devfolio.co"
DEVFOLIO_OPEN = f"{DEVFOLIO_BASE}/hackathons/open"
DEVFOLIO_UPCOMING = f"{DEVFOLIO_BASE}/hackathons/upcoming"

SKIP_TITLES = {
    "applications open", "open", "upcoming", "past",
    "all open hackathons", "all upcoming hackathons",
}


def _parse_devfolio_date(text: str) -> str:
    """Parse 'Starts 27/08/26' into YYYY-MM-DD."""
    match = re.search(r'starts?\s+(\d{1,2})/(\d{1,2})/(\d{2,4})', text.lower())
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return ""


def _scrape_page(url: str) -> list[ScrapeItem]:
    """Scrape a single Devfolio listing page."""
    items: list[ScrapeItem] = []
    logger.info(f"Fetching Devfolio: {url}")

    page = StealthyFetcher.fetch(
        url,
        headless=True,
        disable_resources=True,
        network_idle=True,
        timeout=30000,
    )

    if page.status != 200:
        logger.warning(f"Devfolio returned status {page.status} for {url}")
        return items

    # --- Extract card titles + links ---
    cards = page.css('a[class*="Link__LinkBase"]')
    card_data = []
    for card in cards:
        href = card.attrib.get("href", "")
        if ".devfolio.co" not in href:
            continue
        title_el = card.css("h3::text")
        if not title_el:
            continue
        title = clean_text(title_el[0])
        if not title or title.lower() in SKIP_TITLES:
            continue
        card_data.append({"title": title, "link": href})

    # --- Extract start dates in page order ---
    date_els = page.find_by_regex(re.compile(r'Starts \d{1,2}/\d{1,2}/\d{2,4}'), first_match=False)
    dates = [_parse_devfolio_date(str(el.text)) for el in date_els]

    # --- Extract participation counts in page order ---
    part_els = page.find_by_regex(re.compile(r'\+\d+\s*participat', re.IGNORECASE), first_match=False)
    participations = [clean_text(el.text) for el in part_els]

    # --- Extract Online/Offline status in page order ---
    online_els = page.find_by_text("Online", first_match=False, case_sensitive=True)
    offline_els = page.find_by_text("Offline", first_match=False, case_sensitive=True)
    # Build ordered location list by checking which appears first per card
    # Since we can't reliably order them, we'll skip location for now

    # --- Match by position ---
    # Some cards may not have a date (e.g. "Live" cards). We match what we can.
    for i, card in enumerate(card_data):
        deadline = dates[i] if i < len(dates) else ""
        participation = participations[i] if i < len(participations) else ""

        notes_parts = ["Source: Devfolio."]
        if participation:
            notes_parts.append(participation)

        item = ScrapeItem(
            title=card["title"],
            type="Hackathon",
            source="Devfolio",
            link=card["link"],
            deadline=deadline,
            eligibility="Open to all students and developers",
            tags=[],
            notes=" ".join(notes_parts),
        )
        items.append(item)
        logger.info(f"  Found: {card['title']} | {deadline}")

    return items


def scrape_devfolio() -> list[ScrapeItem]:
    """Scrape open and upcoming hackathons from Devfolio."""
    items: list[ScrapeItem] = []
    for url in [DEVFOLIO_OPEN, DEVFOLIO_UPCOMING]:
        try:
            items.extend(_scrape_page(url))
        except Exception as e:
            logger.error(f"Error scraping Devfolio {url}: {e}")

    logger.info(f"Devfolio: scraped {len(items)} hackathons")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_devfolio()
    for item in results:
        print(f"  {item.title} | {item.deadline} | {item.link}")
