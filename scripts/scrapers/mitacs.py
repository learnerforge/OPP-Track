"""
Mitacs scraper.
Scrapes Mitacs Globalink internships in Canada.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
MITACS_URL = "https://www.mitacs.ca/en/programs/globalink"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_mitacs() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Mitacs")
    try:
        resp = httpx.get(MITACS_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("Mitacs failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=MITACS_URL)
    cards = page.css("article, .card, [class*='program'], a[href*='globalink']")
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
        full_url = href if href.startswith("http") else f"https://www.mitacs.ca{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(ScrapeItem(title=f"[Mitacs] {title}", type="Internship", source="Mitacs", link=full_url, deadline="", eligibility="International undergrad students; research internships in Canada", tags=["mitacs", "canada", "internship", "research", "globalink"], location="Canada", organizer="Mitacs", notes="Mitacs Globalink research internships."))

    if not items:
        items.append(ScrapeItem(title="Mitacs Globalink Internships", type="Internship", source="Mitacs", link=MITACS_URL, deadline="", eligibility="International undergrad students; research in Canada", tags=["mitacs", "canada", "internship", "research"], location="Canada", organizer="Mitacs", notes="Visit link for current programs."))
    items = deduplicate_by_link(items)
    logger.info("Mitacs: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_mitacs()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
