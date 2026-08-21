"""
ETHGlobal hackathon scraper.
ETHGlobal is a Next.js App Router site — event data is embedded in the
React Server Components flight payload (self.__next_f.push chunks), not in
__NEXT_DATA__. Falls back to regex-scraping event links from raw HTML.
"""

from __future__ import annotations

import re
import json
import sys
import logging
from datetime import datetime

import httpx

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

ETHGLOBAL_BASE = "https://ethglobal.com"
ETHGLOBAL_EVENTS_URL = f"{ETHGLOBAL_BASE}/events"

BASE_TAGS = ["web3", "ethereum", "blockchain"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}

FLIGHT_CHUNK_RE = re.compile(
    r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)'
)
EVENT_LINK_RE = re.compile(r'href="/events/([a-z0-9\-]+)"')


def _parse_iso_date(iso: str) -> str:
    """Convert an ISO datetime like '2026-11-03T18:29:00.000Z' to 'YYYY-MM-DD'."""
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def _extract_flight_payload(html: str) -> str | None:
    """Reassemble the RSC flight payload from self.__next_f.push script chunks."""
    chunks = FLIGHT_CHUNK_RE.findall(html)
    if not chunks:
        return None
    try:
        return "".join(json.loads(f'"{chunk}"') for chunk in chunks)
    except json.JSONDecodeError as e:
        logger.debug(f"  Flight chunk decode error: {e}")
        return None


def _extract_events_array(payload: str) -> list[dict]:
    """Locate the '"events":[' key and parse the balanced JSON array after it."""
    idx = payload.find('"events":[')
    if idx < 0:
        return []
    start = idx + len('"events":')
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(payload)):
        ch = payload[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                try:
                    events = json.loads(payload[start:i + 1])
                    return events if isinstance(events, list) else []
                except json.JSONDecodeError as e:
                    logger.debug(f"  Events array parse error: {e}")
                    return []
    return []


def _map_event(event: dict) -> ScrapeItem | None:
    """Map a single ETHGlobal event dict to a ScrapeItem."""
    title = (event.get("name") or "").strip()
    slug = (event.get("slug") or "").strip()
    if not title or not slug:
        return None

    medium = (event.get("medium") or "").lower()
    location = "Online" if medium == "virtual" else "Offline"

    start = _parse_iso_date(event.get("startTime", ""))
    end = _parse_iso_date(event.get("endTime", ""))
    date_range = f"{start} to {end}" if start and end else ""

    notes_parts = []
    if date_range:
        notes_parts.append(date_range)
    notes_parts.append("Source: ETHGlobal")

    return ScrapeItem(
        title=title,
        type="Hackathon",
        source="ETHGlobal",
        link=f"{ETHGLOBAL_BASE}/events/{slug}",
        deadline=_parse_iso_date(event.get("signupDeadline", "")),
        eligibility="Open to all",
        tags=list(BASE_TAGS),
        location=location,
        notes=", ".join(notes_parts),
    )


def _scrape_flight(html: str) -> list[ScrapeItem]:
    """Extract upcoming hackathons from the RSC flight payload."""
    payload = _extract_flight_payload(html)
    if not payload:
        logger.warning("ETHGlobal: could not extract RSC flight payload")
        return []

    events = _extract_events_array(payload)
    logger.info(f"ETHGlobal: parsed {len(events)} total events from flight data")

    future = [e for e in events if e.get("status") == "future"]
    hackathons = [e for e in future if e.get("type") == "hackathon"]
    selected = hackathons or future
    logger.info(f"ETHGlobal: {len(future)} upcoming ({len(hackathons)} hackathons)")

    items: list[ScrapeItem] = []
    for event in selected:
        item = _map_event(event)
        if item:
            errors = item.validate()
            if errors:
                logger.debug(f"  Skipping invalid item {item.title}: {errors}")
                continue
            items.append(item)
            logger.info(f"  Found: {item.title} | {item.deadline} | {item.location}")
    return items


def _scrape_html_fallback(html: str) -> list[ScrapeItem]:
    """Last-resort: extract event slugs from anchor tags in the raw HTML."""
    items: list[ScrapeItem] = []
    seen: set[str] = set()
    for slug in EVENT_LINK_RE.findall(html):
        if slug in seen:
            continue
        seen.add(slug)
        title = slug.replace("-", " ").strip().title()
        item = ScrapeItem(
            title=title,
            type="Hackathon",
            source="ETHGlobal",
            link=f"{ETHGLOBAL_BASE}/events/{slug}",
            deadline="",
            eligibility="Open to all",
            tags=list(BASE_TAGS),
            location="",
            notes="Source: ETHGlobal",
        )
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        items.append(item)
        logger.info(f"  Found (fallback): {item.title}")
    return items


def scrape_ethglobal() -> list[ScrapeItem]:
    """Scrape upcoming hackathons from ETHGlobal via RSC flight data, with HTML fallback."""
    items: list[ScrapeItem] = []
    logger.info(f"Fetching ETHGlobal: {ETHGLOBAL_EVENTS_URL}")

    try:
        resp = httpx.get(ETHGLOBAL_EVENTS_URL, timeout=30, follow_redirects=True, headers=HEADERS)
        if resp.status_code != 200:
            logger.warning(
                f"ETHGlobal returned status {resp.status_code} for {ETHGLOBAL_EVENTS_URL}"
            )
            return items

        items = _scrape_flight(resp.text)
        if not items:
            logger.warning("ETHGlobal flight extraction empty, trying HTML fallback")
            items = _scrape_html_fallback(resp.text)
    except Exception as e:
        logger.error(f"ETHGlobal scrape failed: {e}")

    logger.info(f"ETHGlobal: scraped {len(items)} upcoming hackathons")
    return items


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)
    results = scrape_ethglobal()
    for item in results:
        print(f"  {item.title} | {item.deadline} | {item.location} | {item.link}")
