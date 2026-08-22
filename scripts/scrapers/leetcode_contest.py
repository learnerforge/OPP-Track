"""
LeetCode Contest scraper.
LeetCode hosts weekly and biweekly programming contests.
Uses GraphQL API at /graphql/ to fetch contest data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL = "https://leetcode.com/graphql/"
LEETCODE_CONTEST_URL = "https://leetcode.com/contest/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

CONTESTS_QUERY = """
query contestList {
  brightTitle
  containsPremium
  contests {
    containsPremium
    title
    titleSlug
    startTime
    duration
  }
}
"""


def scrape_leetcode_contest() -> list[ScrapeItem]:
    """Scrape LeetCode contests via GraphQL API."""
    items: list[ScrapeItem] = []
    logger.info("Fetching LeetCode contests")

    try:
        resp = httpx.post(
            LEETCODE_GRAPHQL,
            json={"query": CONTESTS_QUERY},
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
                "Referer": LEETCODE_CONTEST_URL,
            },
        )
    except Exception as e:
        logger.error("LeetCode GraphQL request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("LeetCode GraphQL returned %d", resp.status_code)
        return items

    try:
        data = resp.json()
    except Exception:
        logger.warning("LeetCode returned non-JSON")
        return items

    contests = data.get("data", {}).get("contests", [])
    if not contests:
        logger.warning("No LeetCode contests found")
        return items

    for entry in contests:
        if not isinstance(entry, dict):
            continue

        title = entry.get("title", "").strip()
        title_slug = entry.get("titleSlug", "")
        if not title:
            continue

        contest_url = f"https://leetcode.com/contest/{title_slug}" if title_slug else ""

        # Parse start time (unix timestamp in seconds)
        start_time = entry.get("startTime", 0)
        deadline = ""
        if start_time:
            try:
                deadline = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                pass

        # Duration in seconds
        duration_seconds = entry.get("duration", 0)
        duration_hours = duration_seconds // 3600 if duration_seconds else 0

        # Premium status
        is_premium = entry.get("containsPremium", False)

        tags = ["competitive programming", "leetcode", "algorithms"]
        if is_premium:
            tags.append("premium")

        notes_parts = ["Source: LeetCode."]
        if duration_hours:
            notes_parts.append(f"Duration: {duration_hours} hours.")
        if is_premium:
            notes_parts.append("Contains premium problems.")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="LeetCode",
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
    logger.info("LeetCode: scraped %d contests", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_leetcode_contest()
    print(f"LeetCode: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
