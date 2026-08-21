"""
DoraHacks hackathon scraper.
DoraHacks is a Nuxt SPA — the static HTML only contains banner slides, so the
scraper primarily uses the public hub API (https://dorahacks.io/api/v1/hub/hackathons).
Falls back to parsing the __NUXT_DATA__ payload when the API is unavailable.
"""

from __future__ import annotations

import re
import json
import sys
import logging
from datetime import datetime

import httpx

from scripts.scrapers.base import ScrapeItem, classify_location, deduplicate

logger = logging.getLogger(__name__)

DORA_BASE = "https://dorahacks.io"
DORA_API = f"{DORA_BASE}/api/v1/hub/hackathons"
DORA_PAGE_URL = f"{DORA_BASE}/hackathon"

MAX_PAGES = 3
BASE_TAGS = ["web3", "blockchain", "bounty"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}

PRIZE_SYMBOLS = {"USD": "$", "USDT": "$", "USDC": "$", "EUR": "\u20ac", "GBP": "\u00a3"}

NUXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)
BANNER_PATH_RE = re.compile(r'"/hackathon/([a-zA-Z0-9_\-]+)/?"')


def _format_prize(value, token: str) -> str:
    """Format bonus_price/bonus_token into '$5,000'-style strings."""
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return ""
    if amount <= 0:
        return ""
    symbol = PRIZE_SYMBOLS.get((token or "").upper(), f"{token} " if token else "")
    return f"{symbol}{amount:,}"


def _ts_to_date(ts) -> str:
    """Convert a unix timestamp to 'YYYY-MM-DD' (empty on failure)."""
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


def _is_active(hackathon: dict) -> bool:
    """Keep hackathons that have not ended and have no winners announced yet."""
    if hackathon.get("winner_announced"):
        return False
    end_ts = hackathon.get("timeline_end")
    if end_ts and int(end_ts) < datetime.now().timestamp():
        return False
    return True


def _map_hackathon(h: dict) -> ScrapeItem | None:
    """Map a single DoraHacks API hackathon dict to a ScrapeItem."""
    title = (h.get("title") or "").strip()
    uname = (h.get("uname") or "").strip()
    if not title or not uname:
        return None

    start = _ts_to_date(h.get("timeline_start"))
    end = _ts_to_date(h.get("timeline_end"))
    date_range = f"{start} to {end}" if start and end else ""

    notes_parts = []
    if date_range:
        notes_parts.append(date_range)
    notes_parts.append("Source: DoraHacks")

    venue = (h.get("venue_form") or "").strip()
    location = "Online" if venue.lower() == "virtual" else classify_location(venue)

    tags = list(BASE_TAGS)
    for field in ("tags", "ecosystem"):
        raw = h.get(field) or ""
        if isinstance(raw, str):
            tags.extend(t.strip() for t in raw.split(",") if t.strip())
    seen: set[str] = set()
    tags = [t for t in tags if not (t.lower() in seen or seen.add(t.lower()))][:8]

    owner = h.get("owner") or {}
    participants = ""
    try:
        if int(h.get("hackers_count") or 0) > 0:
            participants = str(h["hackers_count"])
    except (TypeError, ValueError):
        pass

    return ScrapeItem(
        title=title,
        type="Hackathon",
        source="DoraHacks",
        link=f"{DORA_BASE}/hackathon/{uname}/",
        deadline=end,
        eligibility="Open to all",
        tags=tags,
        location=location,
        prize_pool=_format_prize(h.get("bonus_price"), h.get("bonus_token")),
        participants=participants,
        organizer=(owner.get("name") or "").strip(),
        notes=", ".join(notes_parts),
    )


def _scrape_api() -> list[ScrapeItem]:
    """Fetch active hackathons from the DoraHacks hub API (paginated)."""
    items: list[ScrapeItem] = []
    with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
        for page in range(1, MAX_PAGES + 1):
            url = f"{DORA_API}?page={page}"
            logger.info(f"Fetching DoraHacks API: {url}")
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning(f"DoraHacks API returned status {resp.status_code}")
                break
            results = resp.json().get("results", [])
            active_on_page = 0
            for h in results:
                if not _is_active(h):
                    continue
                active_on_page += 1
                item = _map_hackathon(h)
                if item:
                    errors = item.validate()
                    if errors:
                        logger.debug(f"  Skipping invalid item {item.title}: {errors}")
                        continue
                    items.append(item)
                    logger.info(f"  Found: {item.title} | {item.deadline} | {item.prize_pool}")
            if not active_on_page:
                break
    return items


def _scrape_nuxt_fallback(html: str) -> list[ScrapeItem]:
    """Last-resort: extract hackathon slugs from the __NUXT_DATA__ banner payload."""
    items: list[ScrapeItem] = []
    match = NUXT_DATA_RE.search(html)
    if not match:
        return items
    try:
        json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.debug(f"  __NUXT_DATA__ parse error: {e}")
        return items

    slugs = []
    for slug in BANNER_PATH_RE.findall(match.group(1)):
        if slug not in slugs:
            slugs.append(slug)

    for slug in slugs:
        title = slug.replace("-", " ").replace("_", " ").strip().title()
        item = ScrapeItem(
            title=title,
            type="Hackathon",
            source="DoraHacks",
            link=f"{DORA_BASE}/hackathon/{slug}/",
            deadline="",
            eligibility="Open to all",
            tags=list(BASE_TAGS),
            location="Online",
            notes="Source: DoraHacks",
        )
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        items.append(item)
        logger.info(f"  Found (fallback): {item.title}")

    return items


def scrape_dorahacks() -> list[ScrapeItem]:
    """Scrape active hackathons from DoraHacks via API, with HTML fallback."""
    try:
        items = _scrape_api()
        if items:
            items = deduplicate(items)
            logger.info(f"DoraHacks: scraped {len(items)} active hackathons")
            return items
        logger.warning("DoraHacks API returned no items, trying HTML fallback")
    except Exception as e:
        logger.error(f"DoraHacks API error: {e}")

    try:
        logger.info(f"Fetching DoraHacks page: {DORA_PAGE_URL}")
        resp = httpx.get(DORA_PAGE_URL, timeout=30, follow_redirects=True, headers=HEADERS)
        if resp.status_code != 200:
            logger.warning(f"DoraHacks returned status {resp.status_code} for {DORA_PAGE_URL}")
            return []
        items = _scrape_nuxt_fallback(resp.text)
        logger.info(f"DoraHacks: scraped {len(items)} hackathons (HTML fallback)")
        return items
    except Exception as e:
        logger.error(f"DoraHacks scrape failed: {e}")
        return []


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)
    results = scrape_dorahacks()
    for item in results:
        print(f"  {item.title} | {item.deadline} | {item.location} | prize={item.prize_pool} | {item.link}")
