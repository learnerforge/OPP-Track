"""
SWAYAM (India's government MOOC platform) scraper.
The /explorer page is a Polymer SPA — course cards are rendered client-side
via GraphQL, so plain httpx returns an empty shell. StealthyFetcher renders
the page in a real browser; courses live in <course-card> web components.
"""

from __future__ import annotations

import re
import sys
import logging

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, clean_text

logger = logging.getLogger(__name__)

SWAYAM_EXPLORER_URL = "https://swayam.gov.in/explorer"

WEEKS_RE = re.compile(r"(\d+)\s*weeks?", re.I)


def _parse_card(card) -> ScrapeItem | None:
    """Map a single SWAYAM <course-card> element to a ScrapeItem."""
    anchor = card.css("a[href]")
    if not anchor:
        return None
    link = (anchor[0].attrib.get("href") or "").strip()
    if not link.startswith("http"):
        return None

    # Full title lives in the tooltip attribute; <strong> holds a truncated copy
    title = ""
    title_span = card.css(".courseTitle span[title]")
    if title_span:
        title = clean_text(title_span[0].attrib.get("title"))
    if not title:
        title_el = card.css(".courseTitle strong")
        if title_el:
            title = clean_text(title_el[0].text)
    if not title:
        return None

    instructor = ""
    institution = ""
    text_spans = card.css(".courseText span[title]")
    if len(text_spans) > 0:
        instructor = clean_text(text_spans[0].attrib.get("title")) or clean_text(text_spans[0].text)
    if len(text_spans) > 1:
        institution = clean_text(text_spans[1].attrib.get("title")) or clean_text(text_spans[1].text)

    duration = ""
    weeks_match = WEEKS_RE.search(clean_text(card.text))
    if not weeks_match:
        # weeks info lives in a nested table — scan cell texts individually
        for cell in card.css("td, span"):
            weeks_match = WEEKS_RE.search(clean_text(cell.text))
            if weeks_match:
                break
    if weeks_match:
        duration = f"{weeks_match.group(1)} Weeks"

    notes_parts = []
    if instructor:
        notes_parts.append(f"Instructor: {instructor}")
    notes_parts.append("Source: SWAYAM")

    return ScrapeItem(
        title=title,
        type="Certification",
        source="SWAYAM",
        link=link,
        deadline="",  # enrollment windows vary per course — not on the card
        eligibility="Open to all",
        tags=["india", "government", "free courses"],
        location="Online",
        organizer=institution,
        duration=duration,
        notes=". ".join(notes_parts),
    )


def scrape_swayam() -> list[ScrapeItem]:
    """Scrape SWAYAM course listings from the JS-rendered explorer page."""
    items: list[ScrapeItem] = []
    logger.info(f"Fetching SWAYAM: {SWAYAM_EXPLORER_URL}")

    try:
        page = StealthyFetcher.fetch(
            SWAYAM_EXPLORER_URL,
            headless=True,
            network_idle=True,
            timeout=60000,
        )
    except Exception as e:
        logger.error(f"Error fetching SWAYAM: {e}")
        return items

    if page.status != 200:
        logger.warning(f"SWAYAM returned status {page.status} for {SWAYAM_EXPLORER_URL}")
        return items

    cards = page.css("course-card")
    logger.info(f"SWAYAM: found {len(cards)} course cards")

    seen_links: set[str] = set()
    for card in cards:
        item = _parse_card(card)
        if not item:
            continue
        link_key = item.link.rstrip("/").lower()
        if link_key in seen_links:
            continue
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        seen_links.add(link_key)
        items.append(item)
        logger.info(f"  Found: {item.title} | {item.organizer} | {item.duration}")

    logger.info(f"SWAYAM: scraped {len(items)} courses")
    return items


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)
    results = scrape_swayam()
    for item in results:
        print(f"  {item.title} | {item.organizer} | {item.duration} | {item.link}")
