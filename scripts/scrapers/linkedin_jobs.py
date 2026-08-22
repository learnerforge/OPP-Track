"""
LinkedIn Jobs scraper.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
LINKEDIN_URL = "https://www.linkedin.com/jobs/search/?keywords=intern&f_TPR=r604800"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_linkedin_jobs() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching LinkedIn Jobs")
    try:
        resp = httpx.get(LINKEDIN_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("LinkedIn failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=LINKEDIN_URL)
    cards = page.css(".base-card, .job-search-card, [class*='job'], article, li")
    seen = set()
    for card in cards:
        link_el = card.css("a[href*='/jobs/view/']")
        if not link_el:
            link_el = card.css("a")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h3, .base-search-card__title, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)
        if not title or len(title) < 3:
            continue
        tl = title.lower()
        if "intern" not in tl and "apprentice" not in tl:
            continue
        full_url = href.split("?")[0] if href.startswith("http") else f"https://www.linkedin.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)

        company_el = card.css(".base-search-card__subtitle, [class*='company']")
        company = clean_text(company_el[0].text) if company_el else ""
        loc_el = card.css("[class*='location']")
        loc = clean_text(loc_el[0].text) if loc_el else ""

        items.append(ScrapeItem(title=f"[LinkedIn] {title}" + (f" -- {company}" if company else ""), type="Internship", source="LinkedIn Jobs", link=full_url, deadline="", eligibility="Students and graduates; global", tags=["linkedin", "internship", "jobs", "professional"], location=loc or "Various", organizer=company, notes="Source: linkedin.com."))

    if not items:
        items.append(ScrapeItem(title="LinkedIn Internships", type="Internship", source="LinkedIn Jobs", link=LINKEDIN_URL, deadline="", eligibility="Students and graduates; global", tags=["linkedin", "internship", "jobs"], location="Various", notes="Visit link for current listings."))
    items = deduplicate_by_link(items)
    logger.info("LinkedIn: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_linkedin_jobs()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
