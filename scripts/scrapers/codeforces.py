"""
Codeforces competitive programming contest scraper.
Uses the official public API (https://codeforces.com/api/contest.list)
to list upcoming contests — no HTML parsing needed.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

CODEFORCES_API = "https://codeforces.com/api/contest.list"


def _format_duration(seconds: int) -> str:
    """Convert durationSeconds into a human-readable 'Xh Ym' string."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes = remainder // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def scrape_codeforces() -> list[ScrapeItem]:
    """Scrape upcoming Codeforces contests via the public API."""
    items: list[ScrapeItem] = []
    logger.info(f"Fetching Codeforces API: {CODEFORCES_API}")

    resp = httpx.get(CODEFORCES_API, timeout=30, follow_redirects=True)
    resp.raise_for_status()

    data = resp.json()
    if data.get("status") != "OK":
        logger.warning(f"Codeforces API returned status: {data.get('status')}")
        return items

    upcoming = [c for c in data.get("result", []) if c.get("phase") == "BEFORE"]
    logger.info(f"Codeforces: found {len(upcoming)} upcoming contests")

    for contest in upcoming:
        contest_id = contest.get("id")
        start_ts = contest.get("startTimeSeconds")
        contest_type = contest.get("type", "CF")
        duration = _format_duration(contest.get("durationSeconds", 0))

        deadline = ""
        if start_ts:
            deadline = datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d")

        notes = (
            f"Duration: {duration}. Type: {contest_type}. Source: Codeforces API"
        )

        item = ScrapeItem(
            title=contest.get("name", f"Contest {contest_id}"),
            type="Competition",
            source="Codeforces",
            link=f"https://codeforces.com/contest/{contest_id}",
            deadline=deadline,
            eligibility="Global participants",
            tags=["competitive programming", "codeforces"],
            location="Online",
            notes=notes,
        )
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        items.append(item)
        logger.info(f"  Found: {item.title} | {deadline} | {duration}")

    logger.info(f"Codeforces: scraped {len(items)} contests")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_codeforces()
    for item in results:
        print(f"  {item.title} | {item.deadline} | {item.link}")
