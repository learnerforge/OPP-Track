"""
Handshake scraper.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
HS_URL = "https://joinhandshake.com/employers/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_handshake() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Handshake")
    try:
        resp = httpx.get(HS_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("Handshake failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=HS_URL)
    cards = page.css("article, .card, [class*='employer'], [class*='job'], a[href]")
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
        full_url = href if href.startswith("http") else f"https://joinhandshake.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(ScrapeItem(title=f"[Handshake] {title}", type="Internship", source="Handshake", link=full_url, deadline="", eligibility="College students; US-focused", tags=["handshake", "college", "internship", "career"], location="Various", notes="College career platform. Source: joinhandshake.com."))

    if not items:
        items.append(ScrapeItem(title="Handshake Career Opportunities", type="Internship", source="Handshake", link=HS_URL, deadline="", eligibility="College students; US-focused", tags=["handshake", "college", "internship"], location="Various", notes="Visit link for opportunities via your school."))
    items = deduplicate_by_link(items)
    logger.info("Handshake: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_handshake()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
