"""
Analytics Vidhya DataHack competitions scraper.
The DataHack platform (www.analyticsvidhya.com/datahack) is a Next.js app
backed by a GraphQL gateway. Two methods are attempted:
  1. GraphQL 'filteredTournament' query via /api/query-galaxy/ (all pages)
  2. __NEXT_DATA__ JSON payload embedded in the hackathon listing page
"""

from __future__ import annotations

import re
import json
import logging
from datetime import datetime

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline

logger = logging.getLogger(__name__)

AV_BASE = "https://www.analyticsvidhya.com"
AV_HACKATHON_URLS = [
    "https://www.analyticsvidhya.com/datahack/hackathon",
    "https://datahack.analyticsvidhya.com/",
    "https://data.analyticsvidhya.com/competitions",
]
AV_GRAPHQL_URL = f"{AV_BASE}/api/query-galaxy/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

PAGE_SIZE = 6

GRAPHQL_QUERY = (
    "query MyQuery { activeHackathonTournament: filteredTournament( "
    'status: "active" tournamentType: "hackathon" filter: "all" '
    "page: {page} limit: {limit} ) "
    "{ tournamentData { companyLogo prize slug registrationCount startDate endDate "
    "teamsCount thumbnailImage title } totalPages totalTournamentCount } }"
)

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
    re.DOTALL,
)


def _parse_iso_date(iso: str) -> str:
    """Convert an ISO datetime like '2026-12-31T04:29:00+00:00' to YYYY-MM-DD."""
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return parse_deadline(iso)


def _is_placeholder_deadline(iso: str) -> bool:
    """Detect the platform's end-of-year deadline placeholder.

    Analytics Vidhya assigns eternally-open practice problems a fixed
    end-of-year deadline (e.g. '2026-12-31T...') regardless of when they
    actually began. Such dates are NOT real contest deadlines and must not be
    emitted as if the contest were newly active.
    """
    if not iso:
        return False
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        parsed = parse_deadline(iso)
        try:
            dt = datetime.strptime(parsed, "%Y-%m-%d")
        except ValueError:
            return False
    return dt.month == 12 and dt.day == 31


def _map_tournament(t: dict) -> ScrapeItem | None:
    """Map a single tournamentData dict to a ScrapeItem."""
    title = (t.get("title") or "").strip()
    slug = (t.get("slug") or "").strip()
    if not title or not slug:
        return None

    # 'prize' holds either an amount ('₹60,000') or a category label
    # ('Practice Problem', 'Knowledge') — route it accordingly.
    raw_prize = (t.get("prize") or "").strip()
    prize_pool = raw_prize if re.search(r"\d", raw_prize) else ""
    notes_parts = ["Source: Analytics Vidhya DataHack."]
    if raw_prize and not prize_pool:
        notes_parts.append(f"Type: {raw_prize}.")
    if prize_pool:
        notes_parts.append(f"Prize: {prize_pool}.")

    registration_count = t.get("registrationCount")
    participants = str(registration_count) if registration_count else ""

    return ScrapeItem(
        title=title,
        type="Competition",
        source="Analytics Vidhya",
        link=f"{AV_BASE}/datahack/contest/{slug}/",
        deadline=_parse_iso_date(t.get("endDate", "")),
        eligibility="Open to all",
        tags=["machine learning", "data science", "india"],
        location="Online",
        prize_pool=prize_pool,
        participants=participants,
        notes=" ".join(notes_parts),
    )


def _fetch_via_graphql() -> list[dict]:
    """Fetch all active hackathons via the GraphQL gateway, paginated."""
    tournaments: list[dict] = []
    total_pages = 1
    page = 1

    while page <= total_pages:
        # .replace() rather than .format() — the query is full of literal braces
        query = GRAPHQL_QUERY.replace("{page}", str(page)).replace("{limit}", str(PAGE_SIZE))
        resp = httpx.post(
            AV_GRAPHQL_URL,
            headers={"User-Agent": USER_AGENT},
            data={"query": query, "source": "newcompetition"},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning(f"AV GraphQL page {page} returned status {resp.status_code}")
            break

        payload = resp.json()
        if payload.get("errors"):
            logger.warning(f"AV GraphQL errors on page {page}: {payload['errors'][0].get('message')}")
            break

        result = (payload.get("data") or {}).get("activeHackathonTournament") or {}
        data = result.get("tournamentData") or []
        logger.info(
            f"  AV GraphQL page {page}: {len(data)} competitions "
            f"(total {result.get('totalTournamentCount', '?')})"
        )
        tournaments.extend(data)

        try:
            total_pages = int(result.get("totalPages") or 1)
        except (TypeError, ValueError):
            total_pages = 1
        page += 1

    return tournaments


def _fetch_via_next_data() -> list[dict]:
    """Fallback: extract page-1 hackathons from the __NEXT_DATA__ payload."""
    for url in AV_HACKATHON_URLS:
        logger.info(f"Fetching Analytics Vidhya page: {url}")
        try:
            resp = httpx.get(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                timeout=30,
                follow_redirects=True,
            )
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            continue
        if resp.status_code != 200:
            logger.warning(f"Analytics Vidhya returned status {resp.status_code} for {url}")
            continue

        match = NEXT_DATA_RE.search(resp.text)
        if not match:
            logger.warning(f"Analytics Vidhya: no __NEXT_DATA__ found at {url}")
            continue
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.debug(f"  __NEXT_DATA__ parse error: {e}")
            continue

        tournaments = (
            data.get("props", {})
            .get("pageProps", {})
            .get("activeHackathonListSsr", {})
            .get("tournamentData")
        )
        if tournaments:
            logger.info(f"  AV __NEXT_DATA__: {len(tournaments)} competitions (page 1 only)")
            return tournaments

    return []


def scrape_analytics_vidhya() -> list[ScrapeItem]:
    """Scrape active competitions from the Analytics Vidhya DataHack platform."""
    logger.info(f"Scraping Analytics Vidhya DataHack via {AV_GRAPHQL_URL}")

    try:
        tournaments = _fetch_via_graphql()
    except Exception as e:
        logger.error(f"AV GraphQL method failed: {e}")
        tournaments = []

    if not tournaments:
        logger.info("AV GraphQL yielded nothing — falling back to __NEXT_DATA__")
        tournaments = _fetch_via_next_data()

    if not tournaments:
        logger.error("Analytics Vidhya: no competition data found")
        return []

    items: list[ScrapeItem] = []
    seen_titles: set[str] = set()
    today = datetime.now().date()
    for t in tournaments:
        # Drop eternally-open practice problems whose deadline is the
        # platform's end-of-year placeholder (not a real contest deadline).
        if _is_placeholder_deadline(t.get("endDate", "")):
            logger.debug(f"  Skipping placeholder-deadline item: {t.get('title')}")
            continue
        item = _map_tournament(t)
        if not item or item.title in seen_titles:
            continue
        # Only current/upcoming contests: a real deadline must be today or later.
        if item.deadline:
            try:
                dl = datetime.strptime(item.deadline, "%Y-%m-%d").date()
                if dl < today:
                    logger.debug(f"  Skipping ended contest: {item.title} ({item.deadline})")
                    continue
            except ValueError:
                pass
        else:
            # No real end date available -> cannot confirm it is active.
            logger.debug(f"  Skipping contest without a real deadline: {item.title}")
            continue
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        seen_titles.add(item.title)
        items.append(item)
        logger.info(
            f"  Found: {item.title} | {item.deadline or 'no deadline'} | "
            f"{item.participants} registrations"
        )

    logger.info(f"Analytics Vidhya: scraped {len(items)} competitions")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_analytics_vidhya()
    for item in results:
        print(
            f"  {item.title} | {item.deadline or 'ongoing'} | "
            f"{item.participants} regs | {item.prize_pool or '-'} | {item.link}"
        )
