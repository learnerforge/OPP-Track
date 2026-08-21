"""
HackerRank scraper.
Fetches the /domains page and parses its __NEXT_DATA__ payload, then pulls
upcoming contests from HackerRank's own REST endpoint. Company-run contests
are hiring challenges — mapped as type="Hackathon"; community contests are
mapped as type="Competition".
"""

from __future__ import annotations

import re
import json
import logging
from datetime import datetime

import httpx

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

HR_BASE = "https://www.hackerrank.com"
HR_DOMAINS_URL = f"{HR_BASE}/domains"
HR_CONTESTS_API = f"{HR_BASE}/rest/contests/upcoming"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)


def _extract_next_data(html: str) -> dict | None:
    """Extract and parse the __NEXT_DATA__ JSON payload from raw HTML."""
    match = NEXT_DATA_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.debug(f"  __NEXT_DATA__ JSON parse error: {e}")
        return None


def _fetch_domain_catalog() -> list[str]:
    """Fetch /domains and return practice domain names from __NEXT_DATA__."""
    try:
        resp = httpx.get(HR_DOMAINS_URL, timeout=30, follow_redirects=True, headers=HEADERS)
        if resp.status_code != 200:
            logger.warning(f"HackerRank /domains returned status {resp.status_code}")
            return []
        data = _extract_next_data(resp.text)
        if not data:
            logger.warning("HackerRank: could not extract __NEXT_DATA__ from /domains")
            return []
        contest = (
            data.get("props", {})
            .get("pageProps", {})
            .get("prefetchedData", {})
            .get("contest", {})
        )
        tracks = contest.get("tracks") or []
        domains = [t.get("name", "").strip() for t in tracks if t.get("name")]
        logger.info(f"HackerRank: /domains catalog has {len(domains)} practice domains")
        return domains
    except Exception as e:
        logger.debug(f"  /domains fetch error: {e}")
        return []


def _iso_date(iso: str) -> str:
    """Convert an ISO datetime like '2026-09-12T12:30:00Z' to 'YYYY-MM-DD'."""
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def _epoch_date(seconds) -> str:
    """Convert an epoch timestamp to 'YYYY-MM-DD'."""
    if not seconds:
        return ""
    try:
        return datetime.fromtimestamp(int(seconds)).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return ""


def _map_contest(contest: dict) -> ScrapeItem | None:
    """Map a single HackerRank contest dict to a ScrapeItem."""
    title = (contest.get("name") or "").strip()
    slug = (contest.get("slug") or "").strip()
    if not title or not slug:
        return None

    # Company-run contests are hiring challenges
    organization = (contest.get("organization_name") or "").strip()
    is_hiring_challenge = bool(organization) or contest.get("organization_type") == "company"

    start_date = _iso_date(contest.get("get_starttimeiso", "")) or _epoch_date(
        contest.get("epoch_starttime")
    )
    end_date = _iso_date(contest.get("get_endtimeiso", "")) or _epoch_date(
        contest.get("epoch_endtime")
    )

    if is_hiring_challenge:
        item_type = "Hackathon"
        tags = ["coding", "hiring challenge"]
    else:
        item_type = "Competition"
        tags = ["coding", "contest"]

    notes_parts = []
    if start_date and end_date:
        notes_parts.append(f"Runs {start_date} to {end_date}")
    elif end_date:
        notes_parts.append(f"Ends {end_date}")
    if organization:
        notes_parts.append(f"Organizer: {organization}")
    notes_parts.append("Source: HackerRank")

    return ScrapeItem(
        title=title,
        type=item_type,
        source="HackerRank",
        link=f"{HR_BASE}/contests/{slug}",
        deadline=start_date,
        eligibility="Open to all",
        tags=tags,
        location="Online",
        organizer=organization,
        notes=". ".join(notes_parts),
    )


def scrape_hackerrank() -> list[ScrapeItem]:
    """Scrape upcoming HackerRank contests and hiring challenges."""
    items: list[ScrapeItem] = []

    # Primary page per spec — also confirms site reachability
    domains = _fetch_domain_catalog()

    logger.info(f"Fetching HackerRank contests API: {HR_CONTESTS_API}")
    try:
        resp = httpx.get(HR_CONTESTS_API, timeout=30, follow_redirects=True, headers=HEADERS)
        if resp.status_code != 200:
            logger.warning(f"HackerRank API returned status {resp.status_code} for {HR_CONTESTS_API}")
            return items
        data = resp.json()
    except Exception as e:
        logger.error(f"Error fetching HackerRank contests: {e}")
        return items

    contests = data.get("models", [])
    logger.info(f"HackerRank: found {len(contests)} contests in upcoming feed")

    skipped = 0
    for contest in contests:
        # The feed mixes in long-ended contests — keep only live/upcoming ones
        if contest.get("archived") or contest.get("ended"):
            skipped += 1
            continue
        item = _map_contest(contest)
        if not item:
            continue
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        items.append(item)
        label = "hiring challenge" if item.type == "Hackathon" else "contest"
        logger.info(f"  Found: {item.title} | {item.deadline} | {label}")

    if skipped:
        logger.info(f"  Skipped {skipped} archived/ended contests")
    if domains:
        logger.debug(f"  Practice domains available: {', '.join(domains[:8])}...")

    logger.info(f"HackerRank: scraped {len(items)} contests")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackerrank()
    for item in results:
        print(f"  {item.title} | {item.type} | {item.deadline} | {item.organizer} | {item.link}")
