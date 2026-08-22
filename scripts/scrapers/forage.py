"""
Forage scraper.
Scrapes Forage (formerly InsideSherpa) virtual internships.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
FORAGE_URL = "https://www.theforage.com/virtual-internships"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_forage() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Forage")
    try:
        resp = httpx.get(FORAGE_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("Forage failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=FORAGE_URL)
    cards = page.css("a[href*='/virtual-internships/'], [class*='program'], article, .card")
    seen = set()
    for card in cards:
        link_el = card.css("a[href*='/virtual-internships/']")
        if not link_el:
            link_el = card.css("a")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)
        if not title or len(title) < 3:
            continue
        full_url = href if href.startswith("http") else f"https://www.theforage.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)

        company_el = card.css("[class*='company']")
        company = clean_text(company_el[0].text) if company_el else ""

        items.append(ScrapeItem(title=f"[Forage] {title}" + (f" -- {company}" if company else ""), type="Internship", source="Forage", link=full_url, deadline="", eligibility="Students worldwide; free virtual programs", tags=["forage", "virtual", "internship", "simulation", "free"], location="Online", organizer=company, notes="Virtual work simulation programs. Source: theforage.com."))

    if not items:
        items.append(ScrapeItem(title="Forage Virtual Internships", type="Internship", source="Forage", link=FORAGE_URL, deadline="", eligibility="Students worldwide; free virtual programs", tags=["forage", "virtual", "internship", "free"], location="Online", notes="Visit link for current programs."))
    items = deduplicate_by_link(items)
    logger.info("Forage: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_forage()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
