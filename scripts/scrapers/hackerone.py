"""
HackerOne scraper.
Scrapes public bug bounty opportunities from the "Opportunity Discovery" page.
Each program is an <article> card containing the program name and a link
to the team page (/handle?type=team). Programs are always-open bug bounties.
"""

from __future__ import annotations

import logging

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HACKERONE_URL = "https://hackerone.com/opportunities/all"
HACKERONE_BASE = "https://hackerone.com"

FETCH_ARGS = {
    "headless": True,
    "network_idle": True,
    "timeout": 45000,
}


def scrape_hackerone() -> list[ScrapeItem]:
    """Scrape public HackerOne bug bounty programs."""
    items: list[ScrapeItem] = []
    logger.info("Fetching HackerOne opportunities: %s", HACKERONE_URL)

    try:
        page = StealthyFetcher.fetch(HACKERONE_URL, **FETCH_ARGS)
    except Exception as e:
        logger.error("HackerOne fetch failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("HackerOne returned %d", page.status)
        return items

    cards = page.css("article")
    seen_links = set()

    for card in cards:
        # Program name: <span title="Name"...>Name</span> near the top of the card
        name = ""
        span_els = card.css("span[title]")
        if span_els:
            name = clean_text(span_els[0].attrib.get("title", ""))
        if not name:
            title_span = card.css("span.w-0.grow.truncate")
            if title_span:
                name = clean_text(title_span[0].get_all_text())
        if not name or len(name) < 2:
            continue

        # Program link: <a href="/handle?type=team">
        link_el = card.css("a[href*='?type=team']")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        if not href.startswith("/"):
            continue
        full_url = f"{HACKERONE_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        item = ScrapeItem(
            title=f"[HackerOne] {name}",
            type="Competition",
            source="HackerOne",
            link=full_url,
            deadline="",
            eligibility="Open to registered researchers",
            tags=["bug bounty", "hackerone"],
            location="Online",
            notes="Source: HackerOne. Always-open bug bounty program.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("HackerOne: scraped %d programs", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackerone()
    print(f"HackerOne: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title} | {item.link}")
