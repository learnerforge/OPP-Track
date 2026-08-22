"""
AIcrowd scraper.
AIcrowd hosts ML/AI research challenges, often affiliated with NeurIPS, KDD, etc.
The challenges page at aicrowd.com/challenges lists active and past challenges.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

AICROWD_URL = "https://www.aicrowd.com/challenges"
AICROWD_BASE = "https://www.aicrowd.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_aicrowd() -> list[ScrapeItem]:
    """Scrape AIcrowd challenges."""
    items: list[ScrapeItem] = []
    logger.info("Fetching AIcrowd challenges: %s", AICROWD_URL)

    try:
        resp = httpx.get(
            AICROWD_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("AIcrowd request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("AIcrowd returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=AICROWD_URL)

    # AIcrowd challenge cards
    cards = page.css(".challenge-tile, .challenge-card, [class*='challenge'], article")
    seen_links = set()

    for card in cards:
        # Get title and link
        link_el = card.css("a[href*='/challenges/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{AICROWD_BASE}{href}"
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

        # Try to find tags/categories
        tag_els = card.css("[class*='tag'], [class*='category'], .badge")
        tags = ["ai", "machine learning"]
        for tag_el in tag_els[:5]:
            tag_text = clean_text(tag_el.text)
            if tag_text and len(tag_text) < 30:
                tags.append(tag_text.lower())

        # Check for NeurIPS/KDD affiliation
        card_text = clean_text(card.text).lower()
        if "neurips" in card_text:
            tags.append("neurips")
        if "kdd" in card_text:
            tags.append("kdd")

        notes_parts = ["Source: AIcrowd."]
        if prize_pool:
            notes_parts.append(f"Prize: {prize_pool}.")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="AIcrowd",
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
    logger.info("AIcrowd: scraped %d challenges", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_aicrowd()
    print(f"AIcrowd: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
