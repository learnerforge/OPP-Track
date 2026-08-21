"""
AngelHack hackathon scraper (global hackathon series).
angelhack.com sits behind Cloudflare (plain httpx gets a 403 challenge page),
and /hackathons/ now redirects to a B2B services page — the actual event
listing lives at https://angelhack.com/events/, so this scraper tries:
  1. httpx against the events page (works only if Cloudflare is bypassed)
  2. scrapling StealthyFetcher (headless browser) as fallback
Events are WordPress/Elementor loop items (div.e-loop-item) whose CSS classes
carry event-status-* and event-type-*; each card shows a type label, title,
start/end dates, location and region.
"""

from __future__ import annotations

import re
import logging
from urllib.parse import urljoin

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

ANGELHACK_URL = "https://angelhack.com/events/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

DATE_TEXT_RE = re.compile(r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}")
STATUS_CLASS_RE = re.compile(r"event-status-([\w-]+)")


def _is_cloudflare_block(resp: httpx.Response) -> bool:
    """Detect Cloudflare 'Just a moment...' interstitials."""
    return resp.status_code in (403, 503) or "Just a moment" in resp.text[:2000]


def _parse_loop_item(loop) -> ScrapeItem | None:
    """Parse one Elementor loop item into a ScrapeItem."""
    link_els = loop.css('a[href*="/event/"]')
    if not link_els:
        return None
    href = link_els[0].attrib.get("href", "")
    if not href:
        return None
    link = urljoin("https://angelhack.com/", href)

    title_els = loop.css("h2.elementor-heading-title") or loop.css(
        "h3.elementor-heading-title"
    )
    title = clean_text(title_els[0].text if title_els else "")
    if not title:
        return None

    # Heading paragraphs hold every card field: type label, dates,
    # location and region — classify each by content
    event_type = ""
    location = ""
    region = ""
    dates: list[str] = []
    for p in loop.css("p.elementor-heading-title"):
        p_text = clean_text(p.text)
        if not p_text:
            continue
        if DATE_TEXT_RE.fullmatch(p_text):
            dates.append(p_text)
        elif not event_type and p.find("span"):
            event_type = p_text
        elif p_text.lower() in ("virtual", "in person", "hybrid", "online"):
            location = p_text
        else:
            region = region or p_text

    deadline = ""
    if len(dates) >= 2:
        deadline = parse_deadline(dates[-1])
    elif len(dates) == 1:
        deadline = parse_deadline(dates[0])

    status_match = STATUS_CLASS_RE.search(loop.attrib.get("class", ""))
    status = status_match.group(1).replace("-", " ").title() if status_match else ""

    notes_parts = ["Source: AngelHack."]
    if status:
        notes_parts.append(f"Status: {status}.")
    if len(dates) >= 2:
        notes_parts.append(f"Runs {dates[0]} – {dates[-1]}.")
    if region:
        notes_parts.append(f"Region: {region}.")

    tags = ["hackathon"]
    if event_type and event_type.lower() not in ("hackathon",):
        tags.append(event_type.lower())

    return ScrapeItem(
        title=title,
        type="Hackathon",
        source="AngelHack",
        link=link,
        deadline=deadline,
        eligibility="Open to all",
        tags=tags,
        notes=" ".join(notes_parts),
        location=location,
    )


def _parse_listing(html: str) -> list[ScrapeItem]:
    """Extract all event loop items from a rendered events page."""
    from scrapling import Selector

    page = Selector(html)
    items: list[ScrapeItem] = []
    for loop in page.css("div.e-loop-item"):
        try:
            item = _parse_loop_item(loop)
        except Exception as e:
            logger.debug(f"  Card parse error: {e}")
            continue
        if not item:
            continue
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        items.append(item)
        logger.info(
            f"  Found: {item.title} | {item.deadline or 'TBA'} | "
            f"{item.location or '-'} | {item.link}"
        )
    return items


def _fetch_with_httpx() -> str:
    """Fetch the events page with plain httpx. Returns HTML or ''."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = httpx.get(
        ANGELHACK_URL, headers=headers, timeout=30, follow_redirects=True
    )
    if resp.status_code != 200:
        logger.warning(f"AngelHack httpx returned status {resp.status_code}")
        return ""
    if _is_cloudflare_block(resp):
        logger.warning("AngelHack httpx hit a Cloudflare challenge page")
        return ""
    return resp.text


def _fetch_with_browser() -> str:
    """Fetch the events page with a stealth headless browser."""
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        logger.warning("scrapling not installed — browser fallback unavailable")
        return ""

    page = StealthyFetcher.fetch(
        ANGELHACK_URL,
        headless=True,
        network_idle=True,
        timeout=30000,
    )
    if page.status != 200:
        logger.warning(f"AngelHack browser fetch returned status {page.status}")
        return ""
    return str(page.body or "")


def scrape_angelhack() -> list[ScrapeItem]:
    """Scrape hackathons from the AngelHack events listing page."""
    logger.info(f"Fetching AngelHack: {ANGELHACK_URL}")

    html = ""
    for fetcher in (_fetch_with_httpx, _fetch_with_browser):
        try:
            html = fetcher()
        except Exception as e:
            logger.error(f"AngelHack fetcher {fetcher.__name__} failed: {e}")
            html = ""
        if html:
            break

    if not html:
        logger.error("AngelHack: all fetch methods failed")
        return []

    items = deduplicate_by_link(_parse_listing(html))
    logger.info(f"AngelHack: scraped {len(items)} events")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_angelhack()
    for item in results:
        print(
            f"  {item.title} | {item.deadline or 'TBA'} | "
            f"{item.location or '-'} | {item.link}"
        )
