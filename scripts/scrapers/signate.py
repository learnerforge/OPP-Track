"""
SIGNATE scraper.
SIGNATE is Japan's largest data science competition platform.
The competitions page at signate.jp lists active challenges.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

SIGNATE_URL = "https://signate.jp/competitions"
SIGNATE_BASE = "https://signate.jp"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_signate() -> list[ScrapeItem]:
    """Scrape SIGNATE competitions."""
    items: list[ScrapeItem] = []
    logger.info("Fetching SIGNATE competitions: %s", SIGNATE_URL)

    try:
        resp = httpx.get(
            SIGNATE_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en,ja;q=0.9"},
        )
    except Exception as e:
        logger.error("SIGNATE request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("SIGNATE returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=SIGNATE_URL)

    # SIGNATE competition cards
    cards = page.css(".competition-card, .card, [class*='competition'], article")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/competitions/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{SIGNATE_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Try to find deadline
        deadline_el = card.css("[class*='deadline'], [class*='date'], time, [class*='end']")
        deadline = ""
        if deadline_el:
            deadline_text = clean_text(deadline_el[0].text)
            deadline = parse_deadline(deadline_text)

        # Try to find prize info
        prize_el = card.css("[class*='prize'], [class*='reward']")
        prize_pool = clean_text(prize_el[0].text) if prize_el else ""

        tags = ["data science", "machine learning", "japan"]

        notes_parts = ["Source: SIGNATE."]
        if prize_pool:
            notes_parts.append(f"Prize: {prize_pool}.")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="SIGNATE",
            link=full_url,
            deadline=deadline,
            eligibility="Global participants",
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    # Fallback: parse competition links
    if not items:
        links = page.css("a[href*='/competitions/']")
        for link_el in links:
            href = link_el.attrib.get("href", "")
            title = clean_text(link_el.text)
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else f"{SIGNATE_BASE}{href}"
            if full_url in seen_links:
                continue
            seen_links.add(full_url)

            item = ScrapeItem(
                title=title,
                type="Competition",
                source="SIGNATE",
                link=full_url,
                deadline="",
                eligibility="Global participants",
                tags=["data science", "machine learning", "japan"],
                location="Online",
                notes="Source: SIGNATE.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("SIGNATE: scraped %d competitions", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_signate()
    print(f"SIGNATE: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
