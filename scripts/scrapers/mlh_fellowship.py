"""
MLH Fellowship scraper.
The MLH Fellowship is a 12-week internship program for developers.
The fellowship page at fellowship.mlh.io lists current cohorts.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

MLH_FELLOWSHIP_URL = "https://fellowship.mlh.io/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_mlh_fellowship() -> list[ScrapeItem]:
    """Scrape MLH Fellowship program info."""
    items: list[ScrapeItem] = []
    logger.info("Fetching MLH Fellowship: %s", MLH_FELLOWSHIP_URL)

    try:
        resp = httpx.get(
            MLH_FELLOWSHIP_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("MLH Fellowship request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("MLH Fellowship returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=MLH_FELLOWSHIP_URL)

    # Look for cohort/tracks info
    sections = page.css("section, .track, .cohort, article, div[class*='track'], div[class*='program']")
    seen_links = set()

    for section in sections:
        title_el = section.css("h2, h3, h4, .title, [class*='title']")
        link_el = section.css("a[href*='apply'], a[href*='fellowship']")
        deadline_el = section.css(".deadline, time, [class*='date'], [class*='deadline']")

        title = clean_text(title_el[0].text) if title_el else ""
        if not title or len(title) < 3:
            continue

        href = ""
        if link_el:
            href = link_el[0].attrib.get("href", "")

        deadline_raw = clean_text(deadline_el[0].text) if deadline_el else ""
        deadline = parse_deadline(deadline_raw)

        if href and not href.startswith("http"):
            href = f"https://fellowship.mlh.io{href}"

        if href in seen_links:
            continue
        seen_links.add(href)

        item = ScrapeItem(
            title=f"MLH Fellowship — {title}",
            type="Internship",
            source="MLH Fellowship",
            link=href or MLH_FELLOWSHIP_URL,
            deadline=deadline,
            eligibility="Open-source developers; 18+; enrolled or recently graduated",
            tags=["fellowship", "open source", "mlh", "internship", "stipend"],
            location="Remote",
            notes="12-week paid fellowship. Tracks: Open Source, Skills, Education. Source: fellowship.mlh.io.",
        )
        if not item.validate():
            items.append(item)

    # Fallback: create general entry
    if not items:
        item = ScrapeItem(
            title="MLH Fellowship Program",
            type="Internship",
            source="MLH Fellowship",
            link=MLH_FELLOWSHIP_URL,
            deadline="",
            eligibility="Open-source developers; 18+; enrolled or recently graduated",
            tags=["fellowship", "open source", "mlh", "internship", "stipend"],
            location="Remote",
            notes="12-week paid fellowship. Check site for current cohort. Source: fellowship.mlh.io.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("MLH Fellowship: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_mlh_fellowship()
    print(f"MLH Fellowship: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
