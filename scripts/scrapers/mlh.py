"""
MLH (Major League Hacking) events scraper.
MLH uses Inertia.js — the events page embeds a JSON payload in a
`data-page="app"` attribute containing props.upcomingEvents.
"""

from __future__ import annotations

import re
import json
import logging
from datetime import datetime

import httpx

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

MLH_BASE = "https://www.mlh.com"
MLH_EVENTS_URL = f"{MLH_BASE}/seasons/2027/events/"

INERTIA_PAGE_RE = re.compile(r'data-page="app"[^>]*>(.*?)</script>', re.DOTALL)


def _parse_iso_date(iso: str) -> str:
    """Convert an ISO datetime like '2026-08-28T01:11:11Z' to 'YYYY-MM-DD'."""
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def _build_location(event: dict) -> str:
    """Build 'City, Country' from venueAddress, falling back to location string."""
    address = event.get("venueAddress") or {}
    city = (address.get("city") or "").strip().strip(",")
    country = (address.get("country") or "").strip().strip(",")
    if city and country:
        return f"{city}, {country}"
    if country:
        return country
    if city:
        return city
    return (event.get("location") or "").strip()


def _build_tags(event: dict) -> list[str]:
    """Tags: ['mlh', formatType] + hackathon_focus from customFields."""
    tags = ["mlh"]
    format_type = event.get("formatType")
    if format_type:
        tags.append(format_type)
    custom_fields = event.get("customFields") or {}
    focus = custom_fields.get("hackathon_focus") or []
    if isinstance(focus, list):
        tags.extend(t for t in focus if t)
    return tags


def _extract_inertia_data(html: str) -> dict | None:
    """Extract and parse the Inertia.js page JSON from raw HTML."""
    match = INERTIA_PAGE_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError as e:
        logger.debug(f"  Inertia JSON parse error: {e}")
        return None


def _map_event(event: dict) -> ScrapeItem | None:
    """Map a single MLH event dict to a ScrapeItem."""
    title = (event.get("name") or "").strip()
    if not title:
        return None

    link = event.get("websiteUrl") or ""
    if not link and event.get("url"):
        link = f"{MLH_BASE}{event['url']}"

    format_type = event.get("formatType", "")
    date_range = event.get("dateRange", "")

    notes_parts = []
    if date_range:
        notes_parts.append(date_range)
    if format_type:
        notes_parts.append(format_type)
    notes_parts.append("Source: MLH")

    return ScrapeItem(
        title=title,
        type="Hackathon",
        source="MLH",
        link=link,
        deadline=_parse_iso_date(event.get("startsAt", "")),
        eligibility="Students",
        tags=_build_tags(event),
        location=_build_location(event),
        participants="",
        prize_pool="",
        notes=", ".join(notes_parts),
    )


def scrape_mlh() -> list[ScrapeItem]:
    """Scrape upcoming hackathons from the MLH 2027 season events page."""
    items: list[ScrapeItem] = []
    logger.info(f"Fetching MLH: {MLH_EVENTS_URL}")

    resp = httpx.get(MLH_EVENTS_URL, timeout=30, follow_redirects=True)
    if resp.status_code != 200:
        logger.warning(f"MLH returned status {resp.status_code} for {MLH_EVENTS_URL}")
        return items

    data = _extract_inertia_data(resp.text)
    if not data:
        logger.warning("MLH: could not extract Inertia.js page JSON")
        return items

    upcoming = data.get("props", {}).get("upcomingEvents", [])
    for event in upcoming:
        item = _map_event(event)
        if item:
            items.append(item)
            logger.info(f"  Found: {item.title} | {item.deadline} | {item.location}")

    logger.info(f"MLH: scraped {len(items)} upcoming hackathons")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_mlh()
    for item in results:
        print(f"  {item.title} | {item.deadline} | {item.location} | tags={item.tags} | {item.link}")
