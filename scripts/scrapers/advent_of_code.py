"""
Advent of Code scraper.
Advent of Code is an annual Christmas programming challenge (Dec 1-25).
The /events page lists past years; the current year's event begins on
Dec 1 regardless of when its page goes live. We emit an item only for
upcoming events (start date at or after today).
"""

from __future__ import annotations

import logging
import re
from datetime import date

import httpx

from scripts.scrapers.base import ScrapeItem, deduplicate_by_link

logger = logging.getLogger(__name__)

AOC_URL = "https://adventofcode.com"
AOC_EVENTS_URL = "https://adventofcode.com/events"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_advent_of_code() -> list[ScrapeItem]:
    """Scrape upcoming Advent of Code events."""
    items: list[ScrapeItem] = []
    today = date.today().isoformat()
    current_year = date.today().year
    logger.info("Fetching Advent of Code: %s", AOC_EVENTS_URL)

    try:
        resp = httpx.get(
            AOC_EVENTS_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Advent of Code request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Advent of Code returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=AOC_EVENTS_URL)

    years_found: set[str] = set()
    year_links = page.css("article.event a") or page.css("a[href*='adventofcode.com/20'], a[href*='/20']")
    for link_el in year_links:
        href = link_el.attrib.get("href", "")
        year_match = re.search(r"/(\d{4})", href)
        if not year_match:
            continue
        year = year_match.group(1)
        if year in years_found:
            continue
        years_found.add(year)

        deadline = f"{year}-12-01"
        if deadline < today:
            continue  # past years are stale

        event_url = f"{AOC_URL}/{year}"
        item = ScrapeItem(
            title=f"Advent of Code {year}",
            type="Competition",
            source="Advent of Code",
            link=event_url,
            deadline=deadline,
            eligibility="Global participants",
            tags=["competitive programming", "algorithms", "puzzles", "christmas"],
            location="Online",
            notes="Annual Christmas programming challenge. 25 puzzles released one per day from Dec 1-25. "
                  "Source: Advent of Code.",
        )
        if not item.validate():
            items.append(item)

    # The current year's event page isn't published until ~Nov/Dec,
    # but the schedule is fixed: it always starts Dec 1. Include it.
    if str(current_year) not in years_found and f"{current_year}-12-01" >= today:
        item = ScrapeItem(
            title=f"Advent of Code {current_year}",
            type="Competition",
            source="Advent of Code",
            link=f"{AOC_URL}/{current_year}",
            deadline=f"{current_year}-12-01",
            eligibility="Global participants",
            tags=["competitive programming", "algorithms", "puzzles", "christmas"],
            location="Online",
            notes="Annual Christmas programming challenge. 25 puzzles released one per day from Dec 1-25. "
                  "Source: Advent of Code.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Advent of Code: scraped %d upcoming items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_advent_of_code()
    print(f"Advent of Code: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")