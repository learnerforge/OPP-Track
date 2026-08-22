"""
CodeChef scraper.
CodeChef has a REST API for listing contests:
  https://www.codechef.com/api/list/contests/all?sort_by=START&sorting_order=asc&offset=0&mode=all
Returns past, present, and future contests.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

CODECHEF_API = "https://www.codechef.com/api/list/contests/all"
CODECHEF_BASE = "https://www.codechef.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _fetch_contests(mode: str = "all", offset: int = 0) -> list[dict]:
    """Fetch contests from CodeChef API."""
    try:
        resp = httpx.get(
            CODECHEF_API,
            params={
                "sort_by": "START",
                "sorting_order": "asc",
                "offset": str(offset),
                "mode": mode,
            },
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                for key in ("contests", "data", "future_contests", "present_contests", "past_contests"):
                    if isinstance(data.get(key), list):
                        return data[key]
            if isinstance(data, list):
                return data
    except Exception as e:
        logger.debug("CodeChef API failed: %s", e)
    return []


def scrape_codechef() -> list[ScrapeItem]:
    """Scrape CodeChef contests."""
    items: list[ScrapeItem] = []
    logger.info("Fetching CodeChef contests")

    # Fetch future and present contests
    for status in ["future", "present"]:
        contests = _fetch_contests(mode=status)
        logger.info("CodeChef %s contests: %d", status, len(contests))

        for entry in contests:
            if not isinstance(entry, dict):
                continue

            name = entry.get("name", entry.get("code", "")).strip()
            code = entry.get("code", "")
            if not name and not code:
                continue

            contest_url = f"{CODECHEF_BASE}/contests/{code}" if code else entry.get("url", "")

            # Parse start time (format: "2026-08-25T14:30:00+0000" or unix timestamp)
            start_time = entry.get("start_date", entry.get("start_date2", ""))
            deadline = ""
            if start_time:
                if isinstance(start_time, (int, float)):
                    from datetime import datetime, timezone
                    deadline = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime("%Y-%m-%d")
                else:
                    deadline = parse_deadline(str(start_time))

            duration_seconds = entry.get("duration", 0)
            duration_hours = duration_seconds // 3600 if duration_seconds else 0

            # Determine contest type
            contest_type = entry.get("type", "")
            tags = ["competitive programming", "algorithms"]
            if contest_type:
                tags.append(contest_type.lower())

            notes_parts = ["Source: CodeChef."]
            if duration_hours:
                notes_parts.append(f"Duration: {duration_hours} hours.")

            item = ScrapeItem(
                title=name,
                type="Competition",
                source="CodeChef",
                link=contest_url,
                deadline=deadline,
                eligibility="Global participants",
                tags=tags,
                location="Online",
                notes=" ".join(notes_parts),
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("CodeChef: scraped %d contests", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_codechef()
    print(f"CodeChef: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
