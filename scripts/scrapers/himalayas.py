"""
Himalayas scraper.
Himalayas is a remote job board with detailed company profiles.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HIMALAYAS_URL = "https://himalayas.app/jobs"
HIMALAYAS_BASE = "https://himalayas.app"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_himalayas() -> list[ScrapeItem]:
    """Scrape Himalayas remote jobs with internship filter."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Himalayas: %s", HIMALAYAS_URL)

    try:
        resp = httpx.get(
            HIMALAYAS_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Himalayas request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Himalayas returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=HIMALAYAS_URL)

    cards = page.css(".job-card, .card, [class*='job'], article")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/jobs/']")
        if not link_el:
            link_el = card.css("a")
        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 3:
            continue

        title_lower = title.lower()
        if "intern" not in title_lower and "apprentice" not in title_lower:
            continue

        full_url = href if href.startswith("http") else f"{HIMALAYAS_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        company_el = card.css("[class*='company'], [class*='employer']")
        company = clean_text(company_el[0].text) if company_el else ""

        item = ScrapeItem(
            title=f"[Himalayas] {title}" + (f" -- {company}" if company else ""),
            type="Internship",
            source="Himalayas",
            link=full_url,
            deadline="",
            eligibility="Remote workers worldwide",
            tags=["remote", "internship", "himalayas"],
            location="Remote",
            organizer=company,
            notes="Curated remote jobs. Source: himalayas.app.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Himalayas: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_himalayas()
    print(f"Himalayas: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
