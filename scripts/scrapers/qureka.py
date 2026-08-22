"""
Qureka scraper.
Qureka is India's mobile-first quiz and hackathon platform.
The events page lists ongoing and upcoming events.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

QUREKA_URL = "https://www.qureka.com/"
QUREKA_BASE = "https://www.qureka.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_qureka() -> list[ScrapeItem]:
    """Scrape Qureka events."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Qureka: %s", QUREKA_URL)

    try:
        resp = httpx.get(
            QUREKA_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Qureka request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Qureka returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=QUREKA_URL)

    # Qureka event/hackathon cards
    cards = page.css(".event-card, .card, [class*='event'], [class*='hackathon'], article")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/hackathon'], a[href*='/event'], a[href*='/quiz']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{QUREKA_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Try to find deadline/date
        deadline_el = card.css("[class*='date'], time, [class*='deadline']")
        deadline = ""
        if deadline_el:
            deadline_text = clean_text(deadline_el[0].text)
            deadline = parse_deadline(deadline_text)

        # Try to find prize info
        prize_el = card.css("[class*='prize'], [class*='reward']")
        prize_pool = clean_text(prize_el[0].text) if prize_el else ""

        tags = ["hackathon", "quiz", "india"]

        notes_parts = ["Source: Qureka."]
        if prize_pool:
            notes_parts.append(f"Prize: {prize_pool}.")

        item = ScrapeItem(
            title=title,
            type="Hackathon",
            source="Qureka",
            link=full_url,
            deadline=deadline,
            eligibility="India",
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Qureka: scraped %d events", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_qureka()
    print(f"Qureka: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
