"""
Bugcrowd scraper.
Scrapes public bug bounty programs from bugcrowd.com.
The /programs page redirects to the engagements listing; each program card
is an anchor `/engagements/{slug}` with the program name as its text.
Programs are always-open bug bounties.
"""

from __future__ import annotations

import logging

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

BUGCROWD_URL = "https://bugcrowd.com/programs"
BUGCROWD_BASE = "https://bugcrowd.com"

FETCH_ARGS = {
    "headless": True,
    "disable_resources": True,
    "network_idle": True,
    "timeout": 45000,
}

EXCLUDED_BADGES = {
    "featured",
    "view all",
    "managed",
    "public bug bounty programs",
}


def scrape_bugcrowd() -> list[ScrapeItem]:
    """Scrape Bugcrowd public bug bounty programs."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Bugcrowd programs: %s", BUGCROWD_URL)

    try:
        page = StealthyFetcher.fetch(BUGCROWD_URL, **FETCH_ARGS)
    except Exception as e:
        logger.error("Bugcrowd fetch failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("Bugcrowd returned %d", page.status)
        return items

    links = page.css("a[href*='/engagements/']")
    seen_links = set()

    for link_el in links:
        href = link_el.attrib.get("href", "")
        # Only take direct engagement links like /engagements/{slug}
        path = href.split("?", 1)[0].rstrip("/")
        if not re_path_matches(path):
            continue
        title = clean_text(link_el.get_all_text())
        if not title or len(title) < 3:
            continue
        if title.lower() in EXCLUDED_BADGES:
            continue
        if any(b in title.lower() for b in ("bug bounty program", "managed bug bounty") ) and len(title) > 15:
            pass  # keep full names

        full_url = href if href.startswith("http") else f"{BUGCROWD_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        item = ScrapeItem(
            title=f"[Bugcrowd] {title}",
            type="Competition",
            source="Bugcrowd",
            link=full_url,
            deadline="",
            eligibility="Open to registered researchers",
            tags=["bug bounty", "bugcrowd"],
            location="Online",
            notes="Source: Bugcrowd. Always-open bug bounty program.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Bugcrowd: scraped %d programs", len(items))
    return items


def re_path_matches(path: str) -> bool:
    """Validate the engagement path is a single-slug detail page."""
    from urllib.parse import urlparse
    parsed = urlparse(path)
    segments = [s for s in parsed.path.split("/") if s]
    return len(segments) == 2 and segments[0] == "engagements"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_bugcrowd()
    print(f"Bugcrowd: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title} | {item.link}")
