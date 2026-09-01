"""
CodingNinjas scraper.
CodingNinjas (now Naukri Code 360) hosts weekly coding contests.
Data is available via the public API at naukri.com/code360/api.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

CODINGNINJAS_API = "https://www.naukri.com/code360/api/v3/public_section/contest_list"
CODINGNINJAS_BASE = "https://www.naukri.com/code360/contests"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_codingninjas() -> list[ScrapeItem]:
    """Scrape CodingNinjas contests via the public JSON API."""
    items: list[ScrapeItem] = []
    logger.info("Fetching CodingNinjas contests via API")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Origin": "https://www.naukri.com",
        "Referer": "https://www.naukri.com/code360/contests",
    }

    try:
        resp = httpx.get(
            CODINGNINJAS_API,
            headers=headers,
            timeout=20,
            follow_redirects=True,
        )
    except Exception as e:
        logger.error("CodingNinjas request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("CodingNinjas returned %d", resp.status_code)
        return items

    try:
        data = resp.json()
    except Exception as e:
        logger.error("CodingNinjas JSON parse failed: %s", e)
        return items

    events = data.get("data", {}).get("events", [])
    seen_links = set()

    for ev in events:
        reg_status = ev.get("registration_status", "")
        has_started = ev.get("has_started", False)

        # Only include contests currently open for registration and not started
        if reg_status != "REGISTRATIONS_OPEN" or has_started:
            continue

        name = clean_text(ev.get("name", ""))
        slug = ev.get("slug", "")
        if not name or not slug:
            continue

        full_url = f"{CODINGNINJAS_BASE}/{slug}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Registration end time is the deadline
        reg_end = ev.get("registration_end_time", 0)
        deadline = ""
        if reg_end:
            try:
                deadline = datetime.fromtimestamp(reg_end).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                deadline = ""

        short_desc = clean_text(ev.get("short_desc", "") or "")
        contest_type = clean_text(ev.get("contest_type", "") or "")

        notes_parts = [f"Source: {contest_type or 'Code 360'} coding contest."]
        if short_desc:
            notes_parts.append(short_desc[:200])

        item = ScrapeItem(
            title=f"[CodingNinjas] {name}",
            type="Hackathon",
            source="CodingNinjas",
            link=full_url,
            deadline=deadline,
            eligibility="Open to all students and professionals",
            tags=["coding", "contest", "codingninjas", "code360", "india"],
            location="Online",
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("CodingNinjas: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_codingninjas()
    print(f"CodingNinjas: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:60]}")
