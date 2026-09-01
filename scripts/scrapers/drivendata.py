"""
DrivenData scraper.
DrivenData hosts data science competitions with social impact.
The competitions page at drivendata.org/competitions lists active and past challenges.
"""

from __future__ import annotations

import logging
import re

import httpx
from scrapling import Selector

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

DRIVENDATA_URL = "https://www.drivendata.org/competitions/"
DRIVENDATA_BASE = "https://www.drivendata.org"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _extract_deadline(card) -> str:
    """Extract the competition deadline from the card DOM."""
    deadline_els = card.css(".end-date")
    if not deadline_els:
        return ""

    # Prefer the title attribute (full date) over display text
    title_attr = deadline_els[0].attrib.get("title", "")
    if title_attr and "UTC" in title_attr:
        # e.g. "Sept. 16, 2026, 11:59 p.m. UTC"
        m = re.search(r'([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})', title_attr)
        if m:
            # Normalize abbreviated month names with trailing periods (e.g. "Sept." -> "Sep")
            candidate = re.sub(r'([A-Za-z]+)\.', r'\1', m.group(1))
            parsed = parse_deadline(candidate)
            if parsed:
                return parsed

    text = clean_text(deadline_els[0].get_all_text())
    if not text:
        return ""

    # Text may be like "Closes 27 Aug 2026" or "2 weeks left" or "Closes mid-September"
    m = re.search(r'Closes\s+(.+?)(?:\s*left|\s*$)', text, re.IGNORECASE)
    if m:
        deadline_text = m.group(1).strip()
        parsed = parse_deadline(deadline_text)
        if parsed:
            return parsed

    # Try the raw text as well
    return parse_deadline(text)


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

    page = Selector(resp.text, url=DRIVENDATA_URL)

    # Only parse competitions in the "Active" (open) section
    active_section = page.css("#active_competitions")
    if not active_section:
        logger.warning("No active competitions section found on DrivenData")
        return items

    cards = active_section[0].css(".panel-container")
    seen_links = set()

    for card in cards:
        title_el = card.css(".panel-competition-title a")
        if not title_el:
            continue

        title = clean_text(title_el[0].get_all_text())
        href = title_el[0].attrib.get("href", "")
        if not title or not href or len(title) < 5:
            continue

        # Resolve relative URLs against the DrivenData base
        if href.startswith("http"):
            full_url = href
        else:
            full_url = f"{DRIVENDATA_BASE}{href}" if href.startswith("/") else f"{DRIVENDATA_BASE}/{href}"

        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        deadline = _extract_deadline(card)

        # Extract prize
        prize_el = card.css(".prize strong")
        prize_pool = clean_text(prize_el[0].get_all_text()) if prize_el else ""

        # Extract description
        desc_el = card.css(".row-description")
        description = clean_text(desc_el[0].get_all_text()) if desc_el else ""

        tags = ["data science", "social impact"]
        card_text = f"{title} {description}".lower()
        if any(kw in card_text for kw in ["health", "medical", "disease", "parkinson"]):
            tags.append("health")
        if any(kw in card_text for kw in ["climate", "environment", "energy"]):
            tags.append("climate")
        if any(kw in card_text for kw in ["education", "literacy", "tutoring"]):
            tags.append("education")
        if any(kw in card_text for kw in ["disaster", "emergency", "earthquake"]):
            tags.append("disasters")
        if any(kw in card_text for kw in ["civic", "government"]):
            tags.append("civic")
        if any(kw in card_text for kw in ["poverty", "development"]):
            tags.append("development")
        if "speech" in card_text or "transcription" in card_text:
            tags.append("nlp")
        tags = list(dict.fromkeys(tags))  # deduplicate preserving order

        notes_parts = ["Source: DrivenData."]
        if description:
            notes_parts.append(description[:200] + ".")
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
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:60]}")
