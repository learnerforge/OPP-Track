"""
Hack Club scraper.
Hack Club's community hackathon calendar (https://hackathons.hackclub.com) lists
upcoming high-school hackathons worldwide. It is a Next.js app: the default
"Upcoming" view renders client-side, but the full event list is embedded server-side
in the __NEXT_DATA__ script as props.pageProps.events. Each event carries structured
fields (name, website, start/end ISO timestamps, city/state/country, virtual/hybrid
flags). We parse that JSON and keep events that have not ended yet.

Sources: hackathons.hackclub.com (maintained by Hack Club staff)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, date, timezone

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HACKCLUB_URL = "https://hackathons.hackclub.com"

NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)

DEFAULT_ELIGIBILITY = "High school students (Hack Club community)"


def _parse_iso_date(ts: str) -> str:
    """Convert an ISO-8601 timestamp to a YYYY-MM-DD date string."""
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(ts[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return ""


def _location_for(event: dict) -> str:
    """Map the virtual/hybrid flags to a meaningful location label."""
    if event.get("virtual"):
        return "Online"
    if event.get("hybrid"):
        return "Hybrid"
    parts = [p for p in (event.get("city"), event.get("state"), event.get("country")) if p]
    return "Offline"


def _location_details(event: dict) -> str:
    if event.get("virtual"):
        return "Virtual event"
    parts = [p for p in (event.get("city"), event.get("state"), event.get("country")) if p]
    if event.get("hybrid") and parts:
        return f"Hybrid — {', '.join(parts)}"
    if parts:
        return ", ".join(parts)
    return ""


def _map_event(event: dict) -> ScrapeItem | None:
    title = clean_text(event.get("name"))
    website = clean_text(event.get("website"))
    if not title or not website:
        return None
    if not website.startswith(("http://", "https://")):
        return None

    start = clean_text(event.get("start"))
    end = clean_text(event.get("end"))
    deadline = _parse_iso_date(start)

    location = _location_for(event)
    tags = ["hackathon", "high school", "hack club"]
    if event.get("mlhAssociated"):
        tags.append("mlh")
    if event.get("hack_club_event"):
        tags.append("Hack Club affiliated")

    notes_parts = ["Source: Hack Club community calendar."]
    details = _location_details(event)
    if details:
        notes_parts.append(details)
    if start and end:
        notes_parts.append(f"Runs {_parse_iso_date(start)} to {_parse_iso_date(end)} (UTC).")
    if event.get("hybrid"):
        notes_parts.append("Hybrid event.")

    item = ScrapeItem(
        title=title,
        type="Hackathon",
        source="Hack Club",
        link=website,
        deadline=deadline,
        eligibility=DEFAULT_ELIGIBILITY,
        tags=tags,
        notes=" ".join(notes_parts),
        location=location,
    )
    errors = item.validate()
    if errors:
        logger.debug(f"Hack Club: skipping invalid item {title}: {errors}")
        return None
    return item


def _parse_next_data(html: str) -> list[ScrapeItem]:
    """Extract events from the __NEXT_DATA__ JSON payload."""
    match = NEXT_DATA_RE.search(html)
    if not match:
        logger.warning("Hack Club: __NEXT_DATA__ script not found")
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.warning(f"Hack Club: could not parse __NEXT_DATA__ JSON: {e}")
        return []
    events = data.get("props", {}).get("pageProps", {}).get("events", [])
    if not isinstance(events, list):
        logger.warning("Hack Club: no events list in pageProps")
        return []

    today = date.today()
    items: list[ScrapeItem] = []
    for event in events:
        end = _parse_iso_date(clean_text(event.get("end")))
        try:
            end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else None
        except ValueError:
            end_date = None
        if end_date is not None and end_date < today:
            continue  # skip events that have already ended
        item = _map_event(event)
        if item:
            items.append(item)
    return items


def scrape_hackclub() -> list[ScrapeItem]:
    """Scrape upcoming Hack Club high-school hackathons."""
    logger.info(f"Fetching Hack Club hackathons: {HACKCLUB_URL}")
    try:
        page = StealthyFetcher.fetch(
            HACKCLUB_URL,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=30000,
        )
    except Exception as e:
        logger.error(f"Hack Club fetch failed: {e}")
        return []
    if getattr(page, "status", None) != 200:
        logger.warning(f"Hack Club returned status {getattr(page, 'status', None)}")
        return []

    body = page.body
    html = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body or "")
    items = deduplicate_by_link(_parse_next_data(html))
    logger.info(f"Hack Club: scraped {len(items)} upcoming hackathons")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackclub()
    print(f"Hack Club: {len(results)} items")
    for item in results:
        print(f"  {item.title[:60]} | deadline {item.deadline} | {item.location} | {item.link}")