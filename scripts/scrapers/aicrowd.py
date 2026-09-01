"""
AIcrowd scraper.
Scrapes ML/AI challenges from aicrowd.com/challenges.
Each challenge is a .card-challenge with title, link, deadline (in a
data-original-title attribute), and prize money.
"""

from __future__ import annotations

import logging
import re

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

AICROWD_URL = "https://www.aicrowd.com/challenges"
AICROWD_BASE = "https://www.aicrowd.com"

FETCH_ARGS = {
    "headless": True,
    "disable_resources": True,
    "network_idle": True,
    "timeout": 45000,
}


def _extract_prize(text: str) -> str:
    """Extract the prize amount from text like '$150,000+ Prize Money' or '10,000 AUD Prize Money'."""
    text = clean_text(text)
    if not text:
        return ""
    if "prize money" in text.lower():
        # e.g. "$150,000+ Prize Money"
        amount = text.split("Prize Money")[0].strip()
        return amount
    return text


def scrape_aicrowd() -> list[ScrapeItem]:
    """Scrape AIcrowd challenges."""
    items: list[ScrapeItem] = []
    logger.info("Fetching AIcrowd challenges: %s", AICROWD_URL)

    try:
        page = StealthyFetcher.fetch(AICROWD_URL, **FETCH_ARGS)
    except Exception as e:
        logger.error("AIcrowd fetch failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("AIcrowd returned %d", page.status)
        return items

    cards = page.css(".card-challenge")
    seen_links = set()

    for card in cards:
        title_el = card.css(".card-title a")
        if not title_el:
            continue
        title = clean_text(title_el[0].get_all_text())
        if not title or len(title) < 3:
            continue
        href = title_el[0].attrib.get("href", "")
        if not href:
            continue
        full_url = href if href.startswith("http") else f"{AICROWD_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Deadline from data-original-title attribute on the badge span
        deadline = ""
        badge_spans = card.css("span[data-original-title]")
        for span in badge_spans:
            raw = span.attrib.get("data-original-title", "")
            if raw and re.match(r"\d{4}-\d{2}-\d{2}", raw):
                deadline = parse_deadline(raw[:10])
                break

        # Prize
        prize_el = card.css(".prize-item-cash")
        prize_pool = _extract_prize(prize_el[0].get_all_text()) if prize_el else ""

        # Tags from category badges
        tags = ["ai", "machine learning"]
        tag_els = card.css(".category-group .badge")
        for tag_el in tag_els:
            t = clean_text(tag_el.get_all_text()).lstrip("#")
            if t and len(t) < 30:
                tags.append(t)

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
        print(f"  {item.title} | {item.deadline} | {item.prize_pool} | {item.link}")
