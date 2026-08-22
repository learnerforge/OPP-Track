"""
DAAD RISE scraper.
Scrapes DAAD RISE internships in Germany.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
DAAD_URL = "https://www.daad.de/en/study-and-research-in-germany/scholarships/daad-scholarships/"
RISE_URL = "https://www.daad.de/en/study-and-research-in-germany/scholarships/daad-scholarships/database-of-awarded-candidates/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_daad_rise() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching DAAD RISE")
    try:
        resp = httpx.get(DAAD_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("DAAD RISE failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=DAAD_URL)
    cards = page.css("article, .card, [class*='program'], [class*='scholarship'], a[href*='rise']")
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
        full_url = href if href.startswith("http") else f"https://www.daad.de{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(ScrapeItem(title=f"[DAAD] {title}", type="Internship", source="DAAD RISE", link=full_url, deadline="", eligibility="STEM undergrads; summer research in Germany", tags=["daad", "germany", "internship", "research", "rise", "stem"], location="Germany", organizer="DAAD", notes="DAAD RISE: Research Internships in Science and Engineering."))

    if not items:
        items.append(ScrapeItem(title="DAAD RISE Internships", type="Internship", source="DAAD RISE", link="https://www.daad.de/en/study-and-research-in-germany/scholarships/daad-rise/", deadline="", eligibility="STEM undergrads; summer research in Germany", tags=["daad", "germany", "internship", "research", "rise"], location="Germany", organizer="DAAD", notes="Visit link for current RISE program."))
    items = deduplicate_by_link(items)
    logger.info("DAAD RISE: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_daad_rise()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
