"""
NPTEL (National Programme on Technology Enhanced Learning) scraper.
NPTEL — an IIT/IISc consortium initiative — serves fully server-rendered
HTML (SvelteKit), so plain httpx + DOM parsing is enough. Course cards live
in div.course-card elements with name/discipline/instructor/institute.
"""

from __future__ import annotations

import sys
import logging

import httpx
from scrapling.parser import Selector

from scripts.scrapers.base import ScrapeItem, clean_text

logger = logging.getLogger(__name__)

NPTEL_COURSES_URL = "https://nptel.ac.in/courses"
NPTEL_BASE = "https://nptel.ac.in"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}

MAX_COURSES = 500  # safety cap — the catalog lists 3000+ self-paced courses


def _parse_card(card) -> ScrapeItem | None:
    """Map a single NPTEL course-card element to a ScrapeItem."""
    anchor = card.css("a[href*='/courses/']")
    if not anchor:
        return None
    href = (anchor[0].attrib.get("href") or "").strip()
    if not href:
        return None
    link = href if href.startswith("http") else f"{NPTEL_BASE}{href}"

    name_el = card.css(".name")
    title = clean_text(name_el[0].text) if name_el else ""
    # Strip the 'NOC:' prefix used on National Programme Certification courses
    if title.upper().startswith("NOC:"):
        title = title[4:].strip()
    if not title:
        return None

    discipline = ""
    disc_el = card.css(".discipline")
    if disc_el:
        discipline = clean_text(disc_el[0].text)

    instructor = ""
    institute = ""
    meta_spans = card.css(".meta-data span")
    if len(meta_spans) > 0:
        instructor = clean_text(meta_spans[0].text)
    if len(meta_spans) > 1:
        institute = clean_text(meta_spans[1].text)

    notes_parts = []
    if discipline:
        notes_parts.append(f"Discipline: {discipline}")
    if instructor:
        notes_parts.append(f"Instructor: {instructor}")
    notes_parts.append("Source: NPTEL")

    tags = ["india", "iit", "free courses"]
    if discipline:
        tags.append(discipline.lower().replace(" ", "-"))

    return ScrapeItem(
        title=title,
        type="Certification",
        source="NPTEL",
        link=link,
        deadline="",  # self-paced courses — no enrollment deadline on listing
        eligibility="Open to all",
        tags=tags,
        location="Online",
        organizer=institute,
        notes=". ".join(notes_parts),
    )


def scrape_nptel() -> list[ScrapeItem]:
    """Scrape NPTEL course listings from the server-rendered catalog page."""
    items: list[ScrapeItem] = []
    logger.info(f"Fetching NPTEL: {NPTEL_COURSES_URL}")

    try:
        resp = httpx.get(NPTEL_COURSES_URL, timeout=60, follow_redirects=True, headers=HEADERS)
    except Exception as e:
        logger.error(f"Error fetching NPTEL: {e}")
        return items

    if resp.status_code != 200:
        logger.warning(f"NPTEL returned status {resp.status_code} for {NPTEL_COURSES_URL}")
        return items

    page = Selector(resp.text)
    cards = page.css("div.course-card")
    logger.info(f"NPTEL: found {len(cards)} course cards")

    seen_links: set[str] = set()
    for card in cards:
        if len(items) >= MAX_COURSES:
            logger.warning(f"NPTEL: hit safety cap of {MAX_COURSES} courses")
            break
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

    logger.info(f"NPTEL: scraped {len(items)} courses")
    return items


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)
    results = scrape_nptel()
    for item in results[:50]:
        print(f"  {item.title} | {item.organizer} | {item.link}")
