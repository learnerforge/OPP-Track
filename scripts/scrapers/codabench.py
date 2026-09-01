"""
Codabench scraper — fetches most recent competitions via API,
then checks each for active phases (status != "Previous").
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

CODABENCH_LIST = "https://www.codabench.org/api/competitions/"
CODABENCH_BASE = "https://www.codabench.org"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}


def _fetch_list_page(page: int) -> list[dict]:
    """Fetch one page of the competition list."""
    try:
        resp = httpx.get(
            CODABENCH_LIST,
            params={"page": str(page), "page_size": "100"},
            timeout=30,
            follow_redirects=True,
            headers=HEADERS,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("results", []) if isinstance(data, dict) else data
    except Exception as e:
        logger.debug("List page %d failed: %s", page, e)
        return []


def _get_active_phases(comp_id: int) -> list[dict]:
    """Fetch detail and return non-"Previous" phases with future end dates."""
    try:
        resp = httpx.get(
            f"{CODABENCH_BASE}/api/competitions/{comp_id}/",
            timeout=30,
            headers=HEADERS,
        )
        if resp.status_code != 200:
            return []
        detail = resp.json()
        phases = detail.get("phases", [])
        now = datetime.now(timezone.utc)
        active = []
        for ph in phases:
            status = ph.get("status", "")
            if status == "Previous":
                continue
            end_str = ph.get("end", "")
            if not end_str:
                active.append(ph)
                continue
            try:
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if end_dt > now:
                    active.append(ph)
            except (ValueError, TypeError):
                active.append(ph)
        return active
    except Exception:
        return []


def scrape_codabench() -> list[ScrapeItem]:
    """Scrape Codabench competitions — only active/upcoming ones."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Codabench competitions")

    # Fetch list pages starting from the END (most recent) backwards
    # until we find competitions older than 6 months
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=180)
    recent: list[dict] = []

    # Determine total count
    try:
        resp = httpx.get(
            CODABENCH_LIST,
            params={"page": "1", "page_size": "1"},
            timeout=20,
            headers=HEADERS,
        )
        total = resp.json().get("count", 0) if resp.status_code == 200 else 0
    except Exception:
        total = 0

    pages_to_fetch = min((total // 100) + 2, 5)  # last 3 pages max for speed
    start_page = max(1, (total // 100) + 1 - 2)

    for page in range(start_page, start_page + pages_to_fetch):
        results = _fetch_list_page(page)
        if not results:
            break
        page_old = True
        for comp in results:
            created = comp.get("created_when", "")
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if created_dt > cutoff:
                    page_old = False
                    recent.append(comp)
            except (ValueError, TypeError):
                pass
        if page_old and page > start_page:
            break  # rest of list is too old

    logger.info("Codabench: fetched %d recent competitions", len(recent))

    # Check each for active phases — cap at 10 most recent to stay fast
    for comp in recent[:10]:
        comp_id = comp.get("id")
        title = (comp.get("title") or "").strip()
        if not comp_id or not title:
            continue

        phases = _get_active_phases(comp_id)
        if not phases:
            continue

        comp_url = f"{CODABENCH_BASE}/competitions/{comp_id}"

        # Take the latest phase end date as deadline
        deadline = ""
        for ph in sorted(phases, key=lambda p: p.get("end") or "", reverse=True):
            end_str = ph.get("end", "")
            if end_str:
                deadline = parse_deadline(end_str)
                if deadline:
                    break

        description = comp.get("description", "")
        tags = ["machine learning", "benchmarking"]
        if description:
            desc_lower = description.lower()
            if any(kw in desc_lower for kw in ("nlp", "language", "text")):
                tags.append("nlp")
            if any(kw in desc_lower for kw in ("vision", "image", "video")):
                tags.append("computer vision")
            if any(kw in desc_lower for kw in ("reinforcement", "rl", "game")):
                tags.append("reinforcement learning")

        participants = str(comp.get("participants_count") or "")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="Codabench",
            link=comp_url,
            deadline=deadline,
            eligibility="Global participants",
            tags=tags,
            location="Online",
            participants=participants,
            notes=f"Source: Codabench. Phases: {len(phases)} active.",
        )
        if not item.validate():
            items.append(item)
            logger.info("  Found: %s | %s", title[:60], deadline)

    items = deduplicate_by_link(items)
    logger.info("Codabench: scraped %d active competitions", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_codabench()
    print(f"Codabench: {len(results)} items")
    for item in results[:15]:
        print(f"  {item.title[:60]} | {item.deadline} | {item.link}")
