"""
Flipkart scraper.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
FLIP_URL = "https://www.flipkart.com/careers/internships"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_flipkart() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Flipkart")
    try:
        resp = httpx.get(FLIP_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("Flipkart failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=FLIP_URL)
    cards = page.css("article, .card, [class*='intern'], a[href]")
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
        full_url = href if href.startswith("http") else f"https://www.flipkart.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(ScrapeItem(title=f"[Flipkart] {title}", type="Internship", source="Flipkart", link=full_url, deadline="", eligibility="Students; India-focused", tags=["flipkart", "india", "internship", "ecommerce", "tech"], location="India", organizer="Flipkart", notes="Source: flipkart.com."))

    if not items:
        items.append(ScrapeItem(title="Flipkart Internships", type="Internship", source="Flipkart", link=FLIP_URL, deadline="", eligibility="Students; India-focused", tags=["flipkart", "india", "internship"], location="India", organizer="Flipkart", notes="Visit link for current openings."))
    items = deduplicate_by_link(items)
    logger.info("Flipkart: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_flipkart()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
