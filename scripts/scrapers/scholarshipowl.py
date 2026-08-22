"""
ScholarshipOwl scraper.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
SO_URL = "https://scholarshipowl.com/scholarships"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_scholarshipowl() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching ScholarshipOwl")
    try:
        resp = httpx.get(SO_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("ScholarshipOwl failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=SO_URL)
    cards = page.css("article, .card, [class*='scholarship'], a[href*='scholarship']")
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
        full_url = href if href.startswith("http") else f"https://scholarshipowl.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(ScrapeItem(title=f"[ScholarshipOwl] {title}", type="Internship", source="ScholarshipOwl", link=full_url, deadline="", eligibility="US students; college scholarships", tags=["scholarshipowl", "scholarship", "us", "financial-aid"], location="US", notes="Scholarship matching platform. Source: scholarshipowl.com."))

    if not items:
        items.append(ScrapeItem(title="ScholarshipOwl Scholarships", type="Internship", source="ScholarshipOwl", link=SO_URL, deadline="", eligibility="US students; college scholarships", tags=["scholarshipowl", "scholarship", "us"], location="US", notes="Visit link for scholarship listings."))
    items = deduplicate_by_link(items)
    logger.info("ScholarshipOwl: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_scholarshipowl()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
