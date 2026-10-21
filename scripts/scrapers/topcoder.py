"""
Topcoder scraper.
Topcoder hosts competitive programming and design challenges.
The challenges directory at topcoder.com/challenges lists active challenges (React SPA - StealthyFetcher).
"""

from __future__ import annotations

import logging
import re

from scrapling.fetchers import StealthyFetcher
from scrapling.parser import Selector

from scripts.scrapers.base import (
    ScrapeItem,
    ScrapeBlocked,
    parse_deadline,
    clean_text,
    deduplicate_by_link,
    is_blocked_response,
)

logger = logging.getLogger(__name__)

TOPCODER_URL = "https://www.topcoder.com/challenges"
TOPCODER_BASE = "https://www.topcoder.com"


def _probe() -> int:
    """Cheap reachability check before paying for a headless browser.

    Returns the HTTP status, or 0 when the request itself failed. Decision rule
    (user policy, 2026-10-21): if the site is *reachable* (a 2xx/3xx, or a 4xx
    that is not a block) we proceed to scrape; a hard 403/429/503 means we are
    forbidden — report it and skip rather than burn 45 s on a browser that will
    fail the same way.

    Topcoder's public challenge API was retired (all v4/v5 endpoints return
    ``{"message":"Not Found"}``) and the SPA 404s under a headless browser, so
    this probe is what turns a silent 0-item run into an explicit, logged skip.
    """
    import httpx

    try:
        resp = httpx.get(
            TOPCODER_URL,
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OPP-Track/1.0)"},
        )
    except Exception as e:
        logger.warning("Topcoder probe failed: %s", e)
        return 0
    if is_blocked_response(resp):
        raise ScrapeBlocked(
            f"Topcoder probe returned HTTP {resp.status_code} (forbidden/blocked)",
            source="Topcoder",
            status=resp.status_code,
        )
    return resp.status_code


def _parse_ends(text: str) -> str:
    """Parse 'Ends Sep 02' or 'Ends Sep 02, 2026' into YYYY-MM-DD."""
    if not text:
        return ""
    match = re.search(r'(?:Ends|Due)\s+(\w+\s+\d{1,2},?\s*\d{4})', text)
    if not match:
        match = re.search(r'(?:Ends|Due)\s+(\w+\s+\d{1,2})', text)
    if match:
        return parse_deadline(match.group(1))
    return ""


def _select_first(node, css: str) -> Selector | None:
    """Return first element matching css under node, or None."""
    els = node.css(css)
    return els[0] if els else None


def scrape_topcoder() -> list[ScrapeItem]:
    """Scrape active Topcoder challenges via StealthyFetcher (React SPA).

    Probes first: a blocked/unreachable site raises ``ScrapeBlocked`` so the
    orchestrator records it as blocked instead of a silent 0-item source.
    """
    items: list[ScrapeItem] = []
    logger.info("Fetching Topcoder challenges: %s", TOPCODER_URL)

    status = _probe()
    logger.info("Topcoder probe returned HTTP %s — proceeding to render", status or "no response")

    try:
        page = StealthyFetcher.fetch(
            TOPCODER_URL,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=45000,
        )
    except Exception as e:
        logger.error("Topcoder StealthyFetcher failed: %s", e)
        return items

    if page.status != 200:
        # A rendered page that reports forbidden/not-found is a block, not an
        # empty listing: surface it so it is reported and skipped explicitly.
        raise ScrapeBlocked(
            f"Topcoder render returned HTTP {page.status}",
            source="Topcoder",
            status=page.status,
        )

    seen_links = set()

    title_els = page.css("a.vir_2D[href*='/challenges/']")
    logger.info("Topcoder: found %d challenge tiles", len(title_els))

    for title_el in title_els:
        href = title_el.attrib.get("href", "")
        title = clean_text(title_el.get_all_text())
        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{TOPCODER_BASE}{href}"
        if not full_url.startswith(TOPCODER_BASE):
            continue

        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        container = title_el.parent
        if container is None:
            container = title_el
        for _ in range(6):
            if container is None:
                break
            if container.css(".JV6Mui") and container.css('[aria-label^="Purse"]'):
                break
            container = container.parent
        if container is None:
            container = title_el

        deadline = ""
        ends_el = _select_first(container, ".JV6Mui")
        if ends_el is not None:
            deadline = _parse_ends(clean_text(ends_el.text))

        prize_pool = ""
        purse_el = _select_first(container, '[aria-label^="Purse"]')
        if purse_el is not None:
            raw = re.sub(r'<[^>]+>', '', str(purse_el))
            prize_pool = clean_text(raw).replace("Purse", "").strip()

        tags = ["competitive programming", "topcoder"]
        for tag_el in container.css(".UbryEB span"):
            tag_text = clean_text(tag_el.text)
            if tag_text and tag_text not in ("+1", "+2", "+3") and len(tag_text) < 40:
                tags.append(tag_text.lower())
        tags = list(dict.fromkeys(tags))

        participants = ""
        reg_el = _select_first(container, '[aria-label^="Number of registrants"]')
        if reg_el is not None:
            span = _select_first(reg_el, "span")
            if span is not None:
                participants = clean_text(span.text)

        notes_parts = ["Source: topcoder.com."]
        if participants:
            notes_parts.append(f"Registrants: {participants}.")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="Topcoder",
            link=full_url,
            deadline=deadline,
            eligibility="Global participants",
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            participants=participants,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)
            logger.info("  Found: %s | %s | %s | %s", title[:60], deadline, prize_pool, full_url[:60])

    items = deduplicate_by_link(items)
    logger.info("Topcoder: scraped %d challenges", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_topcoder()
    print(f"Topcoder: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")