"""
Indeed scraper.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
INDEED_URL = "https://www.indeed.com/jobs?q=intern&sort=date"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_indeed() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Indeed")
    try:
        resp = httpx.get(INDEED_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("Indeed failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=INDEED_URL)
    cards = page.css(".job_seen_beacon, .jobsearch-ResultsList li, [class*='job'], article")
    seen = set()
    for card in cards:
        link_el = card.css("a[href*='/rc/clk'], a[href*='/viewjob'], a[id*='job']")
        if not link_el:
            link_el = card.css("a")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2.jobTitle, .jobTitle, [class*='title'] a")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)
        if not title or len(title) < 3:
            continue
        full_url = href if href.startswith("http") else f"https://www.indeed.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)

        company_el = card.css("[data-testid='company-name'], .companyName, [class*='company']")
        company = clean_text(company_el[0].text) if company_el else ""
        loc_el = card.css("[data-testid='text-location'], .companyLocation")
        loc = clean_text(loc_el[0].text) if loc_el else ""

        items.append(ScrapeItem(title=f"[Indeed] {title}" + (f" -- {company}" if company else ""), type="Internship", source="Indeed", link=full_url, deadline="", eligibility="Students and graduates; global", tags=["indeed", "internship", "jobs"], location=loc or "Various", organizer=company, notes="Source: indeed.com."))

    if not items:
        items.append(ScrapeItem(title="Indeed Internships", type="Internship", source="Indeed", link=INDEED_URL, deadline="", eligibility="Students and graduates; global", tags=["indeed", "internship", "jobs"], location="Various", notes="Visit link for current listings."))
    items = deduplicate_by_link(items)
    logger.info("Indeed: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_indeed()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
