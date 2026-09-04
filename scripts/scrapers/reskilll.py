"""
Reskilll scraper.
Scrapes Reskilll for Indian hackathons and contests.

The old /hackathons path returned 404. The live listing is at
https://reskilll.com/allhacks which embeds JSON-LD structured data
(CollectionPage -> ItemList of Event objects) with each hackathon's real
name, startDate, endDate and url. Only events whose endDate is still in the
future (i.e. genuinely active/open) are emitted.
"""

from __future__ import annotations

import json
import re
import logging
from datetime import date

import httpx

from scripts.scrapers.base import ScrapeItem, deduplicate_by_link

logger = logging.getLogger(__name__)

RESKILL_ALLHACKS_URL = "https://reskilll.com/allhacks"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

LD_JSON_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL
)


def _extract_events(html: str) -> list[dict]:
    """Pull the Event objects out of the JSON-LD ItemList block."""
    match = LD_JSON_RE.search(html)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    entity = data.get("mainEntity", {}) or {}
    elements = entity.get("itemListElement", []) or []
    events = [e for e in elements if isinstance(e, dict) and e.get("name")]
    logger.info("Reskilll JSON-LD listed %d events", len(events))
    return events


def scrape_reskilll() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Reskilll: %s", RESKILL_ALLHACKS_URL)
    try:
        resp = httpx.get(
            RESKILL_ALLHACKS_URL,
            timeout=40,
            follow_redirects=True,
            headers={"User-Agent": UA},
        )
    except Exception as e:
        logger.error("Reskilll request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Reskilll returned %d", resp.status_code)
        return items

    events = _extract_events(resp.text)
    today = date.today().isoformat()
    for ev in events:
        end = (ev.get("endDate") or "")[:10]
        if not end or end < today:
            logger.debug("  Skipping ended/undated hackathon: %s", ev.get("name"))
            continue
        title = (ev.get("name") or "").strip()
        url = ev.get("url") or RESKILL_ALLHACKS_URL
        if not title:
            continue
        organizer = ((ev.get("organizer") or {}).get("name")) or ""
        notes_parts = ["Source: reskilll.com."]
        if organizer:
            notes_parts.append(f"Organizer: {organizer}.")
        start = (ev.get("startDate") or "")[:10]
        if start and end and start != end:
            notes_parts.append(f"Event period: {start} to {end}.")

        item = ScrapeItem(
            title=f"[Reskilll] {title}",
            type="Hackathon",
            source="Reskilll",
            link=url,
            deadline=end,
            eligibility="Students; India-focused",
            tags=["reskilll", "hackathon", "india", "contest"],
            location="Online",
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)
            logger.info("  Found: %s | deadline=%s", title, end)

    items = deduplicate_by_link(items)
    logger.info("Reskilll: scraped %d active hackathons", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_reskilll()
    for item in results:
        print(f"  {item.title[:60]} | {item.deadline} | {item.link[:70]}")
