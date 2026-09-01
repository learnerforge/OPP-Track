"""
Bugcrowd scraper.
Scrapes public bug bounty programs from bugcrowd.com.
The /programs page redirects to the engagements listing. Each program is an
<li class="bc-program-card"> containing a title link and a bounty range.
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

    cards = page.css("li.bc-program-card, .bc-program-card")
    seen_links = set()

    for card in cards:
        # Program name + link from the title anchor
        title_el = card.css(".bc-panel__title a")
        if not title_el:
            continue
        title = clean_text(title_el[0].get_all_text())
        if not title or len(title) < 3:
            continue
        href = title_el[0].attrib.get("href", "")
        if not href:
            continue
        full_url = href if href.startswith("http") else f"{BUGCROWD_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Bounty range from the footer
        prize_pool = ""
        footer_el = card.css(".bc-program-card__footer")
        if footer_el:
            ft = clean_text(footer_el[0].get_all_text())
            if ft:
                prize_pool = ft[:60]

        item = ScrapeItem(
            title=f"[Bugcrowd] {title}",
            type="Competition",
            source="Bugcrowd",
            link=full_url,
            deadline="",
            eligibility="Open to registered researchers",
            tags=["bug bounty", "bugcrowd"],
            location="Online",
            prize_pool=prize_pool,
            notes="Source: Bugcrowd. Always-open bug bounty program.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Bugcrowd: scraped %d programs", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_bugcrowd()
    print(f"Bugcrowd: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title} | {item.prize_pool} | {item.link}")
