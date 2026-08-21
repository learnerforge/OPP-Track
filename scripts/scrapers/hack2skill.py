"""
Hack2skill hackathon scraper (Indian hackathon aggregator).
hack2skill.com is a Vite SPA — plain httpx returns an empty <div id="root">
shell, so this scraper tries two methods:
  1. httpx against https://hack2skill.com/hackathons-listing (detected as
     useless when the shell has no /event/ links)
  2. scrapling StealthyFetcher (headless browser) as fallback
Cards are located structurally via their register buttons
(a[data-id*="hackathon-listing"]) because styled-components class names are
unstable; each card carries title, a "Free | Virtual"-style badge and a
"Registrations Ends On:- <date>" line.
"""

from __future__ import annotations

import re
import logging
from urllib.parse import urljoin

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HACK2SKILL_URL = "https://hack2skill.com/hackathons-listing"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

DATE_RE = re.compile(r"[A-Za-z]{3},\s*([A-Za-z]{3}\s+\d{1,2},\s*\d{4})")


def _is_spa_shell(html: str) -> bool:
    """The Vite shell has no server-rendered event links."""
    return "/event/" not in html


def _parse_card(anchor) -> ScrapeItem | None:
    """Parse one Hack2skill card from its register-button anchor."""
    href = anchor.attrib.get("href", "")
    if not href:
        return None
    link = urljoin("https://hack2skill.com/", href)

    # Climb to the card root (featured carousel cards carry a data attr,
    # grid cards are white shadow boxes)
    ancestors = anchor.xpath(
        'ancestor::div[starts-with(@data,"hackathon-listing") '
        'or contains(@class,"boxShadowCustom1")][1]'
    )
    if not ancestors:
        return None
    card = ancestors[0]

    title_els = card.css("p[title]")
    title = clean_text(title_els[0].attrib.get("title", "") if title_els else "")
    if not title:
        title = clean_text(title_els[0].text if title_els else "")
    if not title:
        return None

    # Badge like "Free | In Person" / "Free | Hybrid" / "Free | Virtual"
    badge = ""
    for p in card.css("p"):
        p_text = clean_text(p.text)
        if "|" in p_text and len(p_text) < 40:
            badge = p_text
            break

    location = ""
    fee = ""
    if badge:
        parts = [p.strip() for p in badge.split("|")]
        if parts:
            fee = parts[0]
        if len(parts) > 1:
            location = parts[1]

    # Deadline looks like "Sun, Mar 01, 2026 (IST)"
    card_text = clean_text(card.get_all_text())
    deadline = ""
    date_match = DATE_RE.search(card_text)
    if date_match:
        deadline = parse_deadline(date_match.group(1))

    status = clean_text(anchor.text)

    notes_parts = ["Source: Hack2skill."]
    if status:
        notes_parts.append(f"Status: {status}.")
    if fee:
        notes_parts.append(f"Entry: {fee}.")

    return ScrapeItem(
        title=title,
        type="Hackathon",
        source="Hack2skill",
        link=link,
        deadline=deadline,
        eligibility="Open to all",
        tags=["hackathon"],
        notes=" ".join(notes_parts),
        location=location,
    )


def _parse_listing(html: str) -> list[ScrapeItem]:
    """Extract all hackathon cards from a rendered listing page."""
    from scrapling import Selector

    page = Selector(html)
    items: list[ScrapeItem] = []
    for anchor in page.css('a[data-id*="hackathon-listing"]'):
        try:
            item = _parse_card(anchor)
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
    """Fetch the listing page with plain httpx. Returns HTML or ''."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = httpx.get(
        HACK2SKILL_URL, headers=headers, timeout=30, follow_redirects=True
    )
    if resp.status_code != 200:
        logger.warning(f"Hack2skill httpx returned status {resp.status_code}")
        return ""
    if _is_spa_shell(resp.text):
        logger.warning("Hack2skill httpx got the JS app shell (no event links)")
        return ""
    return resp.text


def _fetch_with_browser() -> str:
    """Fetch the listing page with a stealth headless browser."""
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        logger.warning("scrapling not installed — browser fallback unavailable")
        return ""

    page = StealthyFetcher.fetch(
        HACK2SKILL_URL,
        headless=True,
        network_idle=True,
        timeout=30000,
    )
    if page.status != 200:
        logger.warning(f"Hack2skill browser fetch returned status {page.status}")
        return ""
    return str(page.body or "")


def scrape_hack2skill() -> list[ScrapeItem]:
    """Scrape live hackathons from the Hack2skill listing page."""
    logger.info(f"Fetching Hack2skill: {HACK2SKILL_URL}")

    html = ""
    for fetcher in (_fetch_with_httpx, _fetch_with_browser):
        try:
            html = fetcher()
        except Exception as e:
            logger.error(f"Hack2skill fetcher {fetcher.__name__} failed: {e}")
            html = ""
        if html:
            break

    if not html:
        logger.error("Hack2skill: all fetch methods failed")
        return []

    items = deduplicate_by_link(_parse_listing(html))
    logger.info(f"Hack2skill: scraped {len(items)} hackathons")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hack2skill()
    for item in results:
        print(
            f"  {item.title} | {item.deadline or 'TBA'} | "
            f"{item.location or '-'} | {item.link}"
        )
