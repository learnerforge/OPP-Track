"""
Amazon Jobs scraper.
Scrapes Amazon's career page for internship roles.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

AMAZON_SEARCH_URL = "https://www.amazon.jobs/en/search?offset=0&result_limit=40&sort=relevant&category=internships"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_amazon_jobs() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Amazon Jobs")

    try:
        resp = httpx.get(AMAZON_SEARCH_URL, timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    except Exception as e:
        logger.error("Amazon Jobs request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Amazon Jobs returned %d", resp.status_code)
        item = ScrapeItem(title="Amazon Internships", type="Internship", source="Amazon Jobs", link=AMAZON_SEARCH_URL, deadline="", eligibility="Students and recent graduates; global", tags=["amazon", "internship", "swe", "tech"], location="Various", organizer="Amazon", notes="Visit link to search current openings. Source: amazon.jobs.")
        if not item.validate():
            items.append(item)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=AMAZON_SEARCH_URL)

    cards = page.css(".job-card, .card, [class*='job'], article, tr[data-job-id]")
    seen = set()
    for card in cards:
        link_el = card.css("a[href*='/job/']")
        if not link_el:
            link_el = card.css("a")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title'], [class*='name']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)
        if not title or len(title) < 3:
            continue
        full_url = href if href.startswith("http") else f"https://www.amazon.jobs{href}"
        if full_url in seen:
            continue
        seen.add(full_url)

        location_el = card.css("[class*='location']")
        location = clean_text(location_el[0].text) if location_el else ""

        item = ScrapeItem(
            title=f"[Amazon] {title}", type="Internship", source="Amazon Jobs",
            link=full_url, deadline="", eligibility="Students and recent graduates; global",
            tags=["amazon", "internship", "swe", "tech"], location=location or "Various",
            organizer="Amazon", notes="Source: amazon.jobs.",
        )
        if not item.validate():
            items.append(item)

    if not items:
        item = ScrapeItem(title="Amazon Internships", type="Internship", source="Amazon Jobs", link=AMAZON_SEARCH_URL, deadline="", eligibility="Students and recent graduates; global", tags=["amazon", "internship", "swe", "tech"], location="Various", organizer="Amazon", notes="Visit link for current openings. Source: amazon.jobs.")
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Amazon Jobs: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_amazon_jobs()
    print(f"Amazon Jobs: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
