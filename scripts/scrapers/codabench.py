"""
Codabench scraper — fetches competitions via API (returns a JSON list),
then checks each for active phases (status != "Previous").
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

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


def _fetch_all_competitions() -> list[dict]:
    """Fetch competitions from the API (returns a plain JSON list)."""
    try:
        resp = httpx.get(
            CODABENCH_LIST,
            params={"page": "1", "page_size": "100"},
            timeout=30,
            follow_redirects=True,
            headers=HEADERS,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        # API returns a plain list, not a paginated dict
        if isinstance(data, list):
            return data
        return data.get("results", []) if isinstance(data, dict) else []
    except Exception as e:
        logger.debug("Codabench list fetch failed: %s", e)
        return []


def _get_active_phases(comp_id: int) -> list[dict]:
    """Fetch detail and return non-"Previous" phases with future end dates."""
    try:
        resp = httpx.get(
            f"{CODABENCH_BASE}/api/competitions/{comp_id}/",
            timeout=20,
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

    all_comps = _fetch_all_competitions()
    if not all_comps:
        logger.warning("Codabench: no competitions returned from API")
        return items

    # Sort by most recently created first
    sorted_comps = sorted(
        all_comps,
        key=lambda c: c.get("created_when", ""),
        reverse=True,
    )

    # Only check the 15 most recent for speed
    logger.info("Codabench: %d total competitions, checking 15 most recent", len(sorted_comps))

    for comp in sorted_comps[:15]:
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
