"""
Bugcrowd scraper.
Bugcrowd is a crowdsourced security platform.
The programs page at bugcrowd.com/programs lists public bug bounty programs.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

BUGCROWD_URL = "https://www.bugcrowd.com/programs"
BUGCROWD_BASE = "https://www.bugcrowd.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_bugcrowd() -> list[ScrapeItem]:
    """Scrape Bugcrowd public programs."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Bugcrowd programs: %s", BUGCROWD_URL)

    try:
        resp = httpx.get(
            BUGCROWD_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Bugcrowd request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Bugcrowd returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=BUGCROWD_URL)

    # Bugcrowd program cards
    cards = page.css(".program-card, .card, [class*='program'], article")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/programs/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title'], .program-name")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 3:
            continue

        full_url = href if href.startswith("http") else f"{BUGCROWD_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Try to find max bounty
        bounty_el = card.css("[class*='bounty'], [class*='max'], [class*='reward']")
        prize_pool = clean_text(bounty_el[0].text) if bounty_el else ""

        # Try to find type
        type_el = card.css("[class*='type'], [class*='tag'], .badge")
        program_type = clean_text(type_el[0].text) if type_el else ""

        tags = ["bug bounty", "security", "bugcrowd"]
        if program_type:
            tags.append(program_type.lower())

        notes_parts = ["Source: Bugcrowd."]
        if program_type:
            notes_parts.append(f"Type: {program_type}.")

        item = ScrapeItem(
            title=f"[Bugcrowd] {title}",
            type="Competition",
            source="Bugcrowd",
            link=full_url,
            deadline="",
            eligibility="Security researchers",
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            notes=" ".join(notes_parts),
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
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
