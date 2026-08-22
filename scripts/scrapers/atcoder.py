"""
AtCoder scraper.
AtCoder is a major competitive programming platform based in Japan.
The contest listing page at atcoder.jp/contests/ has an HTML table
with upcoming and recent contests. There are also unofficial APIs.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

ATCODER_URL = "https://atcoder.jp/contests/"
ATCODER_BASE = "https://atcoder.jp"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_atcoder() -> list[ScrapeItem]:
    """Scrape AtCoder contests from the contest listing page."""
    items: list[ScrapeItem] = []
    logger.info("Fetching AtCoder contests: %s", ATCODER_URL)

    try:
        resp = httpx.get(
            ATCODER_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
        )
    except Exception as e:
        logger.error("AtCoder request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("AtCoder returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=ATCODER_URL)

    # Parse upcoming contests table
    upcoming_section = page.css("#contest-table-upcoming")
    if upcoming_section:
        rows = upcoming_section.css("tr")
        for row in rows:
            cols = row.css("td")
            if len(cols) < 4:
                continue

            # Column 0: start time, Column 1: contest name, Column 2: duration, Column 3: rated range
            time_text = clean_text(cols[0].text)
            name_el = cols[1].css("a")
            if name_el:
                name = clean_text(name_el[0].text)
                href = name_el[0].attrib.get("href", "")
            else:
                name = clean_text(cols[1].text)
                href = ""

            duration = clean_text(cols[2].text)
            rated_range = clean_text(cols[3].text) if len(cols) > 3 else ""

            if not name:
                continue

            full_url = href if href.startswith("http") else f"{ATCODER_BASE}{href}"

            # Parse deadline from time_text (format: "2026-08-25 21:00:00+0900")
            deadline = ""
            time_match = re.search(r"(\d{4}-\d{2}-\d{2})", time_text)
            if time_match:
                deadline = time_match.group(1)

            notes_parts = ["Source: AtCoder."]
            if duration:
                notes_parts.append(f"Duration: {duration}.")
            if rated_range and rated_range != "-":
                notes_parts.append(f"Rated range: {rated_range}.")

            item = ScrapeItem(
                title=name,
                type="Competition",
                source="AtCoder",
                link=full_url,
                deadline=deadline,
                eligibility="Global participants",
                tags=["competitive programming", "algorithms", "japan"],
                location="Online",
                notes=" ".join(notes_parts),
            )
            if not item.validate():
                items.append(item)

    # Parse recent contests table
    recent_section = page.css("#contest-table-recent")
    if recent_section:
        rows = recent_section.css("tr")
        for row in rows:
            cols = row.css("td")
            if len(cols) < 4:
                continue

            time_text = clean_text(cols[0].text)
            name_el = cols[1].css("a")
            if name_el:
                name = clean_text(name_el[0].text)
                href = name_el[0].attrib.get("href", "")
            else:
                name = clean_text(cols[1].text)
                href = ""

            duration = clean_text(cols[2].text)

            if not name:
                continue

            full_url = href if href.startswith("http") else f"{ATCODER_BASE}{href}"

            deadline = ""
            time_match = re.search(r"(\d{4}-\d{2}-\d{2})", time_text)
            if time_match:
                deadline = time_match.group(1)

            item = ScrapeItem(
                title=name,
                type="Competition",
                source="AtCoder",
                link=full_url,
                deadline=deadline,
                eligibility="Global participants",
                tags=["competitive programming", "algorithms", "japan"],
                location="Online",
                notes=f"Source: AtCoder. Duration: {duration}." if duration else "Source: AtCoder.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("AtCoder: scraped %d contests", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_atcoder()
    print(f"AtCoder: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
