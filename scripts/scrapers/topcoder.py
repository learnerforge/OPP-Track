"""
Topcoder scraper.
Topcoder has a public API at api.topcoder.com/v5/challenges.
We fetch active/upcoming challenges that are open for registration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

TOPCODER_API = "https://api.topcoder.com/v5/challenges"
TOPCODER_BASE = "https://www.topcoder.com/challenges"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_topcoder() -> list[ScrapeItem]:
    """Scrape Topcoder challenges from the public API."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Topcoder challenges: %s", TOPCODER_API)

    try:
        resp = httpx.get(
            TOPCODER_API,
            params={
                "limit": "100",
                "offset": "0",
                "status": "active",
            },
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
    except Exception as e:
        logger.error("Topcoder API request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Topcoder API returned %d", resp.status_code)
        return items

    try:
        data = resp.json()
    except Exception:
        logger.warning("Topcoder API returned non-JSON")
        return items

    challenges = data if isinstance(data, list) else data.get("data", data.get("result", {}).get("content", []))

    for entry in challenges:
        if not isinstance(entry, dict):
            continue

        name = entry.get("name", "").strip()
        if not name:
            continue

        challenge_id = entry.get("id", "")
        challenge_slug = entry.get("slug", challenge_id)
        challenge_url = f"{TOPCODER_BASE}/{challenge_slug}" if challenge_slug else entry.get("url", "")

        # Parse registration end date
        reg_end = entry.get("registrationEndDate", "")
        deadline = parse_deadline(reg_end) if reg_end else ""

        # Parse challenge type and track
        challenge_type = entry.get("type", "")
        track = entry.get("track", "")

        tags = ["competitive programming", "topcoder"]
        if challenge_type:
            tags.append(challenge_type.lower())
        if track:
            tags.append(track.lower())

        # Determine eligibility
        eligibility = "Global participants"
        if entry.get("difficulty"):
            eligibility += f" ({entry['difficulty']})"

        # Prize pool
        prize_pool = ""
        prize_sets = entry.get("prizeSets", [])
        if prize_sets:
            total = sum(p.get("prize", 0) for ps in prize_sets for p in ps.get("prizes", []))
            if total:
                prize_pool = f"${total:,}"

        # Status
        status = entry.get("currentStatus", entry.get("status", ""))

        notes_parts = ["Source: Topcoder."]
        if status:
            notes_parts.append(f"Status: {status}.")
        if challenge_type:
            notes_parts.append(f"Type: {challenge_type}.")
        if track:
            notes_parts.append(f"Track: {track}.")

        item = ScrapeItem(
            title=name,
            type="Competition",
            source="Topcoder",
            link=challenge_url,
            deadline=deadline,
            eligibility=eligibility,
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Topcoder: scraped %d challenges", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_topcoder()
    print(f"Topcoder: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
