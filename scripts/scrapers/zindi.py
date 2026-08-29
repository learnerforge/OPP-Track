"""
Zindi scraper.
Zindi is Africa's leading data science competition platform (React SPA - StealthyFetcher).
The competitions page at zindi.world/competitions lists open challenges.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta

from scrapling.fetchers import StealthyFetcher
from scrapling.parser import Selector

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

ZINDI_URL = "https://zindi.world/competitions"
ZINDI_BASE = "https://zindi.world"


def _select_first(node: Selector, css: str) -> Selector | None:
    """Return first element matching css under node, or None."""
    els = node.css(css)
    return els[0] if els else None


def _parse_relative(text: str, today) -> str:
    """Parse relative Zindi deadline phrases to an absolute date. Returns '' for closed/review."""
    if not text:
        return ""
    low = text.lower()
    if "completed" in low or "under code review" in low:
        return ""
    days = None
    m = re.search(r'(\d+)\s+days?\s+left', low)
    if m:
        days = int(m.group(1))
    if days is None:
        m = re.search(r'(\d+)\s+weeks?\s+left', low)
        if m:
            days = int(m.group(1)) * 7
    if days is None:
        m = re.search(r'(\d+)\s+months?\s+left', low)
        if m:
            days = int(m.group(1)) * 30
    if days is None:
        m = re.search(r'(\d+)\s+hours?\s+left', low)
        if m:
            days = round(int(m.group(1)) / 24)
    if days is None:
        return ""
    return (today + timedelta(days=days)).strftime("%Y-%m-%d")


def scrape_zindi() -> list[ScrapeItem]:
    """Scrape open Zindi competitions via StealthyFetcher (React SPA)."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Zindi competitions: %s", ZINDI_URL)

    try:
        page = StealthyFetcher.fetch(
            ZINDI_URL,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=45000,
        )
    except Exception as e:
        logger.error("Zindi StealthyFetcher failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("Zindi returned %d", page.status)
        return items

    today = datetime.now(timezone.utc).date()
    seen_links = set()

    cards = page.css(".Competition__container___9d8Mz")
    if not cards:
        cards = page.css("[class*='Competition__container']")
    logger.info("Zindi: found %d competition cards", len(cards))

    for card in cards:
        title_el = _select_first(card, ".Competition__titleLink___FKJO4, [class*='titleLink']")
        if title_el is None:
            continue

        href = title_el.attrib.get("href", "")
        inner = _select_first(title_el, "[class*='titleInner']")
        title = clean_text(inner.get_all_text()) if inner is not None else clean_text(title_el.get_all_text())
        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{ZINDI_BASE}{href}"
        if not full_url.startswith(ZINDI_BASE):
            continue

        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        date_el = _select_first(card, ".Competition__dates___G8c48")
        date_text = clean_text(date_el.text) if date_el is not None else ""
        status = "open"
        if "completed" in date_text.lower():
            status = "completed"
        elif "under code review" in date_text.lower():
            status = "review"

        deadline = _parse_relative(date_text, today)

        reward = ""
        reward_el = _select_first(card, '[data-testid="competition-reward-desktop"]')
        if reward_el is None:
            reward_el = _select_first(card, '[data-testid="competition-reward-mobile"]')
        if reward_el is not None:
            reward = clean_text(reward_el.text)

        badge_el = _select_first(card, ".Competition__badgePill___V9L11")
        badge = clean_text(badge_el.text) if badge_el is not None else ""

        part_el = _select_first(card, ".Competition__participationsText___RFoIi")
        part_text = clean_text(part_el.text) if part_el is not None else ""

        counts = re.findall(r'(\d+)\s+participants', part_text)
        participants = counts[0] if counts else ""

        tags = ["machine learning", "data science", "africa"]
        if badge:
            tags.append(badge.lower())

        notes_parts = ["Source: Zindi Africa."]
        if status != "open":
            notes_parts.append(f"Status: {date_text}.")
        if reward:
            notes_parts.append(f"Prize: {reward}.")
        if participants:
            notes_parts.append(f"Participants: {participants}.")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="Zindi",
            link=full_url,
            deadline=deadline,
            eligibility="Global participants (Africa-focused)",
            tags=tags,
            location="Online",
            prize_pool=reward,
            participants=participants,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)
            if status == "open":
                logger.info("  OPEN: %s | %s | %s", title[:60], deadline, reward)

    items = deduplicate_by_link(items)
    logger.info("Zindi: scraped %d competitions", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_zindi()
    print(f"Zindi: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")