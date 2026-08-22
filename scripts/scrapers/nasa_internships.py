"""
NASA Internships scraper.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
NASA_URL = "https://www.nasa.gov/internships/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_nasa_internships() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching NASA Internships")
    try:
        resp = httpx.get(NASA_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("NASA failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=NASA_URL)
    cards = page.css("article, .card, [class*='intern'], a[href*='intern'], section a")
    seen = set()
    for card in cards:
        link_el = card.css("a[href]")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)
        if not title or len(title) < 3:
            continue
        full_url = href if href.startswith("http") else f"https://www.nasa.gov{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(ScrapeItem(title=f"[NASA] {title}", type="Internship", source="NASA Internships", link=full_url, deadline="", eligibility="US citizens and permanent residents; students", tags=["nasa", "space", "internship", "stem", "government"], location="Various (US)", organizer="NASA", notes="Source: nasa.gov."))

    if not items:
        items.append(ScrapeItem(title="NASA Internships", type="Internship", source="NASA Internships", link="https://intern.nasa.gov/", deadline="", eligibility="US citizens and permanent residents; students", tags=["nasa", "space", "internship", "stem"], location="Various (US)", organizer="NASA", notes="Visit link for current openings."))
    items = deduplicate_by_link(items)
    logger.info("NASA: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_nasa_internships()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
