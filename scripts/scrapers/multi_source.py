"""
multi_source.py — Dynamic scraper driven by sources.json.

Reads the source registry and dispatches to the appropriate fetching
strategy (scrapling / httpx / api) for every enabled source.

Usage:
    python -m scripts.scrapers.multi_source                # all enabled sources
    python -m scripts.scrapers.multi_source --source devpost
    python -m scripts.scrapers.multi_source --type hackathon
    python -m scripts.scrapers.multi_source --region india
    python -m scripts.scrapers.multi_source --list
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from urllib.parse import urljoin
from typing import Any

import httpx
from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import (
    ScrapeItem,
    classify_location,
    clean_text,
    deduplicate,
    parse_deadline,
    quality_score,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES_JSON = Path(__file__).resolve().parent / "sources.json"


# ---------------------------------------------------------------------------
# Source registry helpers
# ---------------------------------------------------------------------------

def load_sources(path: Path = SOURCES_JSON) -> dict:
    """Return the full sources.json contents."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_enabled_sources(
    sources: list[dict],
    *,
    source_id: str | None = None,
    source_type: str | None = None,
    region: str | None = None,
) -> list[dict]:
    """Filter the sources list by enabled flag, id, type, and region."""
    result: list[dict] = []
    for src in sources:
        if not src.get("enabled", False):
            continue
        if source_id and src["id"] != source_id:
            continue
        if source_type and src.get("type", "").lower() != source_type.lower():
            continue
        if region and src.get("region", "").lower() != region.lower():
            continue
        result.append(src)
    return result


def list_sources(sources: list[dict]) -> None:
    """Print a table of all sources and their enabled status."""
    print(f"{'ID':<28} {'Name':<26} {'Type':<16} {'Region':<10} {'Method':<12} {'Enabled'}")
    print("-" * 108)
    for src in sources:
        print(
            f"{src['id']:<28} {src['name']:<26} {src.get('type', ''):<16} "
            f"{src.get('region', ''):<10} {src.get('scrape_method', ''):<12} "
            f"{'yes' if src.get('enabled') else 'no'}"
        )


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

def _resolve_url(href: str, base_url: str) -> str:
    """Turn a possibly-relative href into an absolute URL."""
    if not href:
        return ""
    if href.startswith(("http://", "https://")):
        return href
    return urljoin(base_url, href)


def _extract_text(card: Any, selector: str | None) -> str:
    """Extract text content from a card element using a CSS selector."""
    if not selector:
        return ""
    elements = card.css(selector)
    if not elements:
        return ""
    return clean_text(elements[0].text)


def _extract_text_deep(card: Any, selector: str | None) -> str:
    """Like _extract_text but also strips HTML tags to get nested text."""
    if not selector:
        return ""
    elements = card.css(selector)
    if not elements:
        return ""
    raw = str(elements[0])
    import re
    text = re.sub(r"<[^>]+>", " ", raw)
    return clean_text(text)


def _extract_link(card: Any, selector: str | None, base_url: str) -> str:
    """Extract an href from the first matching element."""
    if not selector:
        return ""
    elements = card.css(selector)
    if not elements:
        return ""
    href = elements[0].attrib.get("href", "")
    return _resolve_url(href, base_url)


def _extract_tags(card: Any, selector: str | None) -> list[str]:
    """Extract multiple tag texts from a repeated selector."""
    if not selector:
        return []
    elements = card.css(selector)
    tags: list[str] = []
    for el in elements:
        t = clean_text(el.text)
        if t:
            tags.append(t)
    return tags


def _extract_items(card: Any, selector: str | None) -> list[str]:
    """Generic helper: extract inner texts for a list of elements."""
    return _extract_tags(card, selector)


# ---------------------------------------------------------------------------
# Generic scrapers per method
# ---------------------------------------------------------------------------

_TYPE_MAP: dict[str, str] = {
    "hackathon": "Hackathon",
    "internship": "Internship",
    "certification": "Certification",
    "scholarship": "Hackathon",  # map to closest valid type
    "fellowship": "Internship",  # map to closest valid type
}


def _scrape_scrapling(source: dict) -> list[ScrapeItem]:
    """Fetch with StealthyFetcher and parse with source-specific CSS selectors."""
    url = source["url"]
    sel = source.get("selectors", {})
    card_sel = sel.get("item") or sel.get("cards")
    if not card_sel:
        logger.warning(f"[{source['id']}] No card selector defined, skipping")
        return []

    logger.info(f"[{source['id']}] Fetching (scrapling): {url}")
    page = StealthyFetcher.fetch(
        url,
        headless=True,
        disable_resources=True,
        network_idle=True,
        timeout=30_000,
    )

    if page.status != 200:
        logger.warning(f"[{source['id']}] HTTP {page.status} from {url}")
        return []

    cards = page.css(card_sel)
    if not cards:
        logger.warning(f"[{source['id']}] No cards matched '{card_sel}'")
        return []

    return _parse_cards(cards, source, url)


def _scrape_httpx(source: dict) -> list[ScrapeItem]:
    """Fetch static HTML with httpx and parse with CSS selectors."""
    url = source["url"]
    sel = source.get("selectors", {})
    card_sel = sel.get("item") or sel.get("cards")
    if not card_sel:
        logger.warning(f"[{source['id']}] No card selector defined, skipping")
        return []

    logger.info(f"[{source['id']}] Fetching (httpx): {url}")
    resp = httpx.get(url, follow_redirects=True, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })

    if resp.status_code != 200:
        logger.warning(f"[{source['id']}] HTTP {resp.status_code} from {url}")
        return []

    # Parse with scrapling even for httpx-fetched HTML (reuse Adaptor)
    from scrapling import Selector
    page = Selector(resp.text, url=url)
    cards = page.css(card_sel)
    if not cards:
        logger.warning(f"[{source['id']}] No cards matched '{card_sel}'")
        return []

    return _parse_cards(cards, source, url)


def _scrape_api(source: dict) -> list[ScrapeItem]:
    """Make a direct API call and try to interpret the JSON response."""
    url = source["url"]
    sel = source.get("selectors", {})
    logger.info(f"[{source['id']}] Fetching (api): {url}")

    resp = httpx.get(url, follow_redirects=True, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    })

    if resp.status_code != 200:
        logger.warning(f"[{source['id']}] HTTP {resp.status_code} from {url}")
        return []

    try:
        data = resp.json()
    except Exception:
        logger.warning(f"[{source['id']}] Response is not valid JSON, falling back to HTML parse")
        return _scrape_httpx(source)

    # The API response structure varies wildly.  We attempt a few common
    # patterns and fall back to an empty list when none match.
    items_list: list[dict] | None = None

    # Pattern 1: top-level list
    if isinstance(data, list):
        items_list = data

    # Pattern 2: {"data": [...]}  or  {"results": [...]}  or  {"items": [...]}
    if items_list is None and isinstance(data, dict):
        for key in ("data", "results", "items", "competitions", "contests",
                     "hackathons", "challenges", "events"):
            candidate = data.get(key)
            if isinstance(candidate, list) and candidate:
                items_list = candidate
                break

    # Pattern 3: nested under a "nodes" key (Relay/GraphQL)
    if items_list is None and isinstance(data, dict):
        for key in ("nodes", "edges"):
            candidate = data.get(key)
            if isinstance(candidate, list) and candidate:
                # edges often have a "node" wrapper
                if isinstance(candidate[0], dict) and "node" in candidate[0]:
                    items_list = [n["node"] for n in candidate]
                else:
                    items_list = candidate
                break

    if not items_list:
        logger.warning(f"[{source['id']}] Could not locate items list in API response")
        return []

    return _parse_api_items(items_list, source)


# ---------------------------------------------------------------------------
# Shared card / API-item parser
# ---------------------------------------------------------------------------

# Map common selector keys → ScrapeItem fields
_SELECTOR_FIELD_MAP = {
    "title": ("title", False),
    "link": ("link", True),       # True = resolve as URL
    "deadline": ("deadline", False),
    "location": ("location", False),
    "prize": ("prize_pool", False),
    "participants": ("participants", False),
    "tags": ("tags", False),
}


def _parse_cards(cards: list, source: dict, base_url: str) -> list[ScrapeItem]:
    """Extract ScrapeItem objects from CSS-matched card elements."""
    sel = source.get("selectors", {})
    opp_type = _TYPE_MAP.get(source.get("type", "").lower(), "Hackathon")
    source_name = source["name"]
    items: list[ScrapeItem] = []
    seen_titles: set[str] = set()

    for card in cards:
        title = _extract_text(card, sel.get("title"))
        if not title or len(title) < 3 or title in seen_titles:
            continue
        seen_titles.add(title)

        link = _extract_link(card, sel.get("link"), base_url)
        if not link:
            link = f"{base_url.rstrip('/')}/search?q={title.replace(' ', '+')}"

        deadline_raw = _extract_text_deep(card, sel.get("deadline"))
        deadline = parse_deadline(deadline_raw) if deadline_raw else ""

        location_raw = _extract_text(card, sel.get("location"))
        location = classify_location(location_raw)

        prize_pool = _extract_text_deep(card, sel.get("prize"))
        participants = _extract_text(card, sel.get("participants"))
        tags = _extract_tags(card, sel.get("tags"))

        # Build notes from available data
        notes_parts = [f"Source: {source_name}."]
        if location_raw:
            notes_parts.append(f"Raw location: {location_raw}.")
        if prize_pool:
            notes_parts.append(f"Prize: {prize_pool}.")

        item = ScrapeItem(
            title=title,
            type=opp_type,
            source=source_name,
            link=link,
            deadline=deadline,
            eligibility="See source for eligibility details",
            tags=tags,
            location=location,
            prize_pool=prize_pool,
            participants=participants,
            notes=" ".join(notes_parts),
        )
        items.append(item)
        logger.debug(
            f"  {title} | {opp_type} | {deadline} | score={quality_score(item)}"
        )

    return items


def _parse_api_items(items_list: list[dict], source: dict) -> list[ScrapeItem]:
    """Extract ScrapeItem objects from a list of JSON dicts (API response)."""
    opp_type = _TYPE_MAP.get(source.get("type", "").lower(), "Hackathon")
    source_name = source["name"]
    base_url = source["url"]
    items: list[ScrapeItem] = []
    seen_titles: set[str] = set()

    for entry in items_list:
        if not isinstance(entry, dict):
            continue

        # Try common title keys
        title = ""
        for key in ("title", "name", "heading", "label", "problem_title"):
            if entry.get(key):
                title = clean_text(str(entry[key]))
                break
        if not title or len(title) < 3 or title in seen_titles:
            continue
        seen_titles.add(title)

        # Try common link keys
        link = ""
        for key in ("url", "link", "href", "permalink", "registration_url"):
            if entry.get(key):
                link = _resolve_url(str(entry[key]), base_url)
                break

        # Try common deadline keys
        deadline = ""
        for key in ("deadline", "end_date", "submission_deadline", "registration_deadline",
                     "last_date", "closes_at"):
            if entry.get(key):
                deadline = parse_deadline(str(entry[key]))
                break

        # Location
        location_raw = ""
        for key in ("location", "venue", "city", "mode"):
            if entry.get(key):
                location_raw = str(entry[key])
                break
        location = classify_location(location_raw)

        # Prize
        prize_pool = ""
        for key in ("prize", "prize_pool", "prizes", "total_prize"):
            val = entry.get(key)
            if val:
                if isinstance(val, (int, float)):
                    prize_pool = f"${val:,.0f}"
                else:
                    prize_pool = str(val)
                break

        # Participants
        participants = ""
        for key in ("participants", "registrations", "teams", "team_count"):
            if entry.get(key):
                participants = str(entry[key])
                break

        # Tags
        tags: list[str] = []
        for key in ("tags", "skills", "categories", "domains"):
            val = entry.get(key)
            if isinstance(val, list):
                tags = [str(t) for t in val if t]
                break

        notes_parts = [f"Source: {source_name}."]
        if location_raw:
            notes_parts.append(f"Raw location: {location_raw}.")

        item = ScrapeItem(
            title=title,
            type=opp_type,
            source=source_name,
            link=link,
            deadline=deadline,
            eligibility="See source for eligibility details",
            tags=tags,
            location=location,
            prize_pool=prize_pool,
            participants=participants,
            notes=" ".join(notes_parts),
        )
        items.append(item)
        logger.debug(
            f"  {title} | {opp_type} | {deadline} | score={quality_score(item)}"
        )

    return items


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def scrape_source(source: dict) -> list[ScrapeItem]:
    """Dispatch to the right scraping strategy for a single source."""
    method = source.get("scrape_method", "").lower()
    if method == "scrapling":
        return _scrape_scrapling(source)
    if method == "httpx":
        return _scrape_httpx(source)
    if method == "api":
        return _scrape_api(source)
    logger.warning(f"[{source['id']}] Unknown scrape_method '{method}', skipping")
    return []


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_multi_source(
    *,
    source_id: str | None = None,
    source_type: str | None = None,
    region: str | None = None,
    delay: float = 2.0,
) -> list[ScrapeItem]:
    """Run all (or a filtered subset of) enabled sources and return items."""
    registry = load_sources()
    sources = registry.get("sources", [])

    targets = get_enabled_sources(
        sources, source_id=source_id, source_type=source_type, region=region,
    )

    if not targets:
        logger.warning("No enabled sources matched the given filters.")
        return []

    logger.info(f"Scraping {len(targets)} source(s) with {delay}s delay between requests")

    all_items: list[ScrapeItem] = []
    succeeded = 0
    failed = 0

    for i, source in enumerate(targets):
        sid = source["id"]
        logger.info(f"[{i + 1}/{len(targets)}] {source['name']} ({source.get('scrape_method')})")
        try:
            items = scrape_source(source)
            all_items.extend(items)
            succeeded += 1
            logger.info(f"[{sid}] OK — {len(items)} items scraped")
        except Exception as exc:
            failed += 1
            logger.error(f"[{sid}] FAILED — {exc}", exc_info=True)

        # Rate-limit between requests (skip after the last one)
        if i < len(targets) - 1:
            time.sleep(delay)

    unique = deduplicate(all_items)
    logger.info(
        f"\nDone. {succeeded} succeeded, {failed} failed. "
        f"{len(all_items)} raw items → {len(unique)} unique."
    )

    # Quality summary
    scores = [quality_score(it) for it in unique]
    if scores:
        avg = sum(scores) / len(scores)
        logger.info(f"Quality scores: avg={avg:.0f} min={min(scores)} max={max(scores)}")

    return unique


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dynamic multi-source scraper driven by sources.json",
    )
    parser.add_argument(
        "--source", type=str, default=None,
        help="Scrape only the source with this ID (e.g. devpost)",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_sources_flag",
        help="List all sources and exit",
    )
    parser.add_argument(
        "--type", type=str, default=None, dest="source_type",
        help="Filter by type (hackathon / internship / certification)",
    )
    parser.add_argument(
        "--region", type=str, default=None,
        help="Filter by region (global / india / us / eu)",
    )
    parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Seconds to wait between source requests (default: 2.0)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Path to write JSON output (default: stdout summary only)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Debug-level logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    registry = load_sources()
    sources = registry.get("sources", [])

    # --list: print table and exit
    if args.list_sources_flag:
        list_sources(sources)
        enabled = [s for s in sources if s.get("enabled")]
        print(f"\n{len(enabled)} of {len(sources)} sources enabled.")
        return

    # Scrape
    items = run_multi_source(
        source_id=args.source,
        source_type=args.source_type,
        region=args.region,
        delay=args.delay,
    )

    # Print results
    if not items:
        logger.info("No items scraped.")
        return

    by_type: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for item in items:
        by_type[item.type] = by_type.get(item.type, 0) + 1
        by_source[item.source] = by_source.get(item.source, 0) + 1

    logger.info("\n--- Summary by type ---")
    for t, c in sorted(by_type.items()):
        logger.info(f"  {t}: {c}")

    logger.info("\n--- Summary by source ---")
    for s, c in sorted(by_source.items()):
        logger.info(f"  {s}: {c}")

    # Optionally write JSON
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([it.to_dict() for it in items], f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(items)} items to {out_path}")


if __name__ == "__main__":
    main()
