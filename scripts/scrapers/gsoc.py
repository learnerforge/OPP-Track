"""
Google Summer of Code scraper.
GSoC is a global program for students to contribute to open source.
The program page at summerofcode.withgoogle.com lists past and current years.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

GSOC_URL = "https://summerofcode.withgoogle.com/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_gsoc() -> list[ScrapeItem]:
    """Scrape Google Summer of Code info."""
    items: list[ScrapeItem] = []
    logger.info("Fetching GSoC: %s", GSOC_URL)

    try:
        resp = httpx.get(
            GSOC_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("GSoC request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("GSoC returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=GSOC_URL)

    # Look for year links or timeline sections
    year_links = page.css("a[href*='/archive/'], a[href*='/program/']")
    seen_years = set()

    for link_el in year_links:
        href = link_el.attrib.get("href", "")
        year_match = re.search(r"/(\d{4})", href)
        if not year_match:
            continue

        year = year_match.group(1)
        if year in seen_years:
            continue
        seen_years.add(year)

        full_url = href if href.startswith("http") else f"https://summerofcode.withgoogle.com{href}"

        item = ScrapeItem(
            title=f"Google Summer of Code {year}",
            type="Internship",
            source="GSoC",
            link=full_url,
            deadline=f"{year}-04-02",  # Typical GSoC deadline
            eligibility="Students 18+ enrolled in or accepted to accredited university; global",
            tags=["gsoc", "open source", "google", "internship", "stipend"],
            location="Remote",
            notes="12-week paid program contributing to open source. Stipend: $1500-$3300. Source: summerofcode.withgoogle.com.",
        )
        if not item.validate():
            items.append(item)

    # Create current/upcoming year entry
    current_year = datetime.now().year
    if current_year not in seen_years:
        item = ScrapeItem(
            title=f"Google Summer of Code {current_year}",
            type="Internship",
            source="GSoC",
            link=GSOC_URL,
            deadline=f"{current_year}-04-02",
            eligibility="Students 18+ enrolled in or accepted to accredited university; global",
            tags=["gsoc", "open source", "google", "internship", "stipend"],
            location="Remote",
            notes="12-week paid program contributing to open source. Stipend: $1500-$3300. Source: summerofcode.withgoogle.com.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("GSoC: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_gsoc()
    print(f"GSoC: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
