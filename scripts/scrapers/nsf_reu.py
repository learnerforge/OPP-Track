"""
NSF REU scraper.
Scrapes NSF Research Experiences for Undergraduates listings.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
NSF_URL = "https://www.nsf.gov/crssprgm/reu/reu_search.jsp"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_nsf_reu() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching NSF REU")
    try:
        resp = httpx.get(NSF_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("NSF REU failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("NSF REU returned %d", resp.status_code)

    from scrapling import Selector
    page = Selector(resp.text, url=NSF_URL)
    rows = page.css("table tr, [class*='reu'], [class*='program'], article")
    seen = set()
    for row in rows:
        link_el = row.css("a[href]")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        title_el = row.css("td:first-child, h2, h3, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)
        if not title or len(title) < 3:
            continue
        full_url = href if href.startswith("http") else f"https://www.nsf.gov{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(ScrapeItem(title=f"[NSF REU] {title}", type="Internship", source="NSF REU", link=full_url, deadline="", eligibility="US undergraduates; STEM research", tags=["nsf", "reu", "research", "stem", "undergrad"], location="Various (US)", organizer="NSF", notes="NSF Research Experiences for Undergraduates."))

    if not items:
        items.append(ScrapeItem(title="NSF REU Programs", type="Internship", source="NSF REU", link=NSF_URL, deadline="", eligibility="US undergraduates; STEM research", tags=["nsf", "reu", "research", "stem"], location="Various (US)", organizer="NSF", notes="Visit link for current REU listings."))
    items = deduplicate_by_link(items)
    logger.info("NSF REU: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_nsf_reu()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
