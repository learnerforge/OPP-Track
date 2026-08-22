"""
DrivenData scraper.
DrivenData hosts data science competitions with social impact.
The competitions page at drivendata.org/competitions lists active and past challenges.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

DRIVENDATA_URL = "https://www.drivendata.org/competitions/"
DRIVENDATA_BASE = "https://www.drivendata.org"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_drivendata() -> list[ScrapeItem]:
    """Scrape DrivenData competitions."""
    items: list[ScrapeItem] = []
    logger.info("Fetching DrivenData competitions: %s", DRIVENDATA_URL)

    try:
        resp = httpx.get(
            DRIVENDATA_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("DrivenData request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("DrivenData returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=DRIVENDATA_URL)

    # DrivenData competition cards
    cards = page.css(".competition-card, .card, [class*='competition'], article, .row")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/competitions/']")
        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{DRIVENDATA_BASE}{href}"
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
        prize_el = card.css("[class*='prize'], [class*='award']")
        prize_pool = clean_text(prize_el[0].text) if prize_el else ""

        # Tags from card text
        card_text = clean_text(card.text).lower()
        tags = ["data science", "social impact"]
        if any(kw in card_text for kw in ["health", "medical", "disease"]):
            tags.append("health")
        if any(kw in card_text for kw in ["climate", "environment", "energy"]):
            tags.append("climate")
        if any(kw in card_text for kw in ["education", "literacy"]):
            tags.append("education")
        if any(kw in card_text for kw in ["disaster", "emergency"]):
            tags.append("disasters")
        if any(kw in card_text for kw in ["civic", "government"]):
            tags.append("civic")
        if any(kw in card_text for kw in ["poverty", "development"]):
            tags.append("development")

        notes_parts = ["Source: DrivenData."]
        if prize_pool:
            notes_parts.append(f"Prize: {prize_pool}.")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="DrivenData",
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

    items = deduplicate_by_link(items)
    logger.info("DrivenData: scraped %d competitions", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_drivendata()
    print(f"DrivenData: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
