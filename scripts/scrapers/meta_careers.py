"""
Meta Careers scraper.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
META_URL = "https://www.metacareers.com/jobs?q=intern"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_meta_careers() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Meta Careers")
    try:
        resp = httpx.get(META_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("Meta Careers failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=META_URL)
    cards = page.css("a[href*='/jobs/'], [class*='job'], article")
    seen = set()
    for card in cards:
        link_el = card.css("a[href*='/jobs/']") or card.css("a")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)
        if not title or len(title) < 3:
            continue
        tl = title.lower()
        if "intern" not in tl and "new grad" not in tl:
            continue
        full_url = href if href.startswith("http") else f"https://www.metacareers.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        loc = clean_text((card.css("[class*='location']") or [None])[0].text) if card.css("[class*='location']") else ""
        items.append(ScrapeItem(title=f"[Meta] {title}", type="Internship", source="Meta Careers", link=full_url, deadline="", eligibility="Students and recent graduates; global", tags=["meta", "facebook", "internship", "swe", "tech"], location=loc or "Various", organizer="Meta", notes="Source: metacareers.com."))

    if not items:
        items.append(ScrapeItem(title="Meta Internships", type="Internship", source="Meta Careers", link=META_URL, deadline="", eligibility="Students and recent graduates; global", tags=["meta", "facebook", "internship"], location="Various", organizer="Meta", notes="Visit link for current openings."))
    items = deduplicate_by_link(items)
    logger.info("Meta Careers: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_meta_careers()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
