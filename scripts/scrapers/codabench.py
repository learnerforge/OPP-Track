"""
Codabench scraper.
Codabench is the successor to CodaLab for ML benchmarking competitions.
Has a REST API at /api/competitions/ for listing public competitions.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

CODABENCH_API = "https://www.codabench.org/api/competitions/"
CODABENCH_BASE = "https://www.codabench.org"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_codabench() -> list[ScrapeItem]:
    """Scrape Codabench competitions via API."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Codabench competitions: %s", CODABENCH_API)

    try:
        resp = httpx.get(
            CODABENCH_API,
            params={"page": "1", "page_size": "50"},
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
    except Exception as e:
        logger.error("Codabench API request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Codabench API returned %d", resp.status_code)
        return items

    try:
        data = resp.json()
    except Exception:
        logger.warning("Codabench returned non-JSON")
        return items

    competitions = data if isinstance(data, list) else data.get("results", data.get("data", []))

    for entry in competitions:
        if not isinstance(entry, dict):
            continue

        title = entry.get("title", entry.get("name", "")).strip()
        if not title:
            continue

        comp_id = entry.get("id", "")
        comp_url = f"{CODABENCH_BASE}/competitions/{comp_id}" if comp_id else entry.get("url", "")

        # Parse dates
        created = entry.get("created_at", entry.get("start_date", ""))
        deadline = ""
        # Look for end date in phases
        phases = entry.get("phases", [])
        for phase in phases:
            end_date = phase.get("end_date", phase.get("deadline", ""))
            if end_date:
                deadline = parse_deadline(end_date)
                break

        # Description/tags
        description = entry.get("description", "")
        tags = ["machine learning", "benchmarking"]
        if description:
            desc_lower = description.lower()
            if any(kw in desc_lower for kw in ["nlp", "language", "text"]):
                tags.append("nlp")
            if any(kw in desc_lower for kw in ["vision", "image", "video"]):
                tags.append("computer vision")
            if any(kw in desc_lower for kw in ["reinforcement", "rl", "game"]):
                tags.append("reinforcement learning")

        # Check if active
        is_active = entry.get("is_active", entry.get("status", ""))
        status_str = ""
        if is_active is True or is_active == "active":
            status_str = "Active"
        elif is_active is False or is_active == "ended":
            status_str = "Ended"

        notes_parts = ["Source: Codabench."]
        if status_str:
            notes_parts.append(f"Status: {status_str}.")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="Codabench",
            link=comp_url,
            deadline=deadline,
            eligibility="Global participants",
            tags=tags,
            location="Online",
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Codabench: scraped %d competitions", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_codabench()
    print(f"Codabench: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
