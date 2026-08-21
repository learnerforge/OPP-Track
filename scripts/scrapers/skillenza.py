"""
Skillenza corporate coding challenge scraper.
NOTE: Skillenza (formerly Venturesity, acquired by Imarticus Learning in 2022)
shut down — skillenza.com expired in March 2025 and no longer resolves. This
scraper still follows the standard two-method flow so it recovers automatically
if the platform or a successor domain comes back:
  1. httpx against https://www.skillenza.com/challenges
  2. scrapling StealthyFetcher (headless browser) as fallback
Parsing is generic (challenge links + card headings) since the original card
markup is unavailable for verification. On failure the scraper logs a clear
warning and returns an empty list.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

SKILLEZA_URL = "https://www.skillenza.com/challenges"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _parse_listing(html: str) -> list[ScrapeItem]:
    """Extract challenge cards generically from a listings page."""
    from scrapling import Selector

    page = Selector(html)
    items: list[ScrapeItem] = []
    seen_links: set[str] = set()

    candidates = page.css('a[href*="challenge"], a[href*="/challenges/"]')
    for anchor in candidates:
        try:
            href = anchor.attrib.get("href", "")
            title = clean_text(anchor.text)
            # Fall back to a heading inside the anchor (card-style markup)
            if not title:
                for tag in ("h2", "h3", "h4"):
                    heads = anchor.css(tag)
                    if heads:
                        title = clean_text(heads[0].text)
                        break
            if not title or len(title) < 4 or not href:
                continue
            link = href if href.startswith("http") else f"https://www.skillenza.com{href}"
            if link in seen_links:
                continue

            # Deadline: first date-like text inside the card
            deadline = ""
            card_text = clean_text(anchor.get_all_text())
            parsed = parse_deadline(card_text[:300])
            if parsed:
                deadline = parsed

            item = ScrapeItem(
                title=title,
                type="Competition",
                source="Skillenza",
                link=link,
                deadline=deadline,
                eligibility="Open to all",
                tags=["challenge", "coding"],
                notes="Source: Skillenza.",
                location="Online",
            )
            errors = item.validate()
            if errors:
                logger.debug(f"  Skipping invalid item {item.title}: {errors}")
                continue
            seen_links.add(link)
            items.append(item)
            logger.info(f"  Found: {item.title} | {item.deadline or 'TBA'} | {item.link}")
        except Exception as e:
            logger.debug(f"  Card parse error: {e}")
            continue
    return deduplicate_by_link(items)


def _fetch_with_httpx() -> str:
    """Fetch the challenges page with plain httpx. Returns HTML or ''."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = httpx.get(
        SKILLEZA_URL, headers=headers, timeout=30, follow_redirects=True
    )
    if resp.status_code != 200:
        logger.warning(f"Skillenza httpx returned status {resp.status_code}")
        return ""
    return resp.text


def _fetch_with_browser() -> str:
    """Fetch the challenges page with a stealth headless browser."""
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        logger.warning("scrapling not installed — browser fallback unavailable")
        return ""

    page = StealthyFetcher.fetch(
        SKILLEZA_URL,
        headless=True,
        network_idle=True,
        timeout=30000,
    )
    if page.status != 200:
        logger.warning(f"Skillenza browser fetch returned status {page.status}")
        return ""
    return str(page.body or "")


def scrape_skillenza() -> list[ScrapeItem]:
    """Scrape challenges from the Skillenza challenges listing page.

    Returns an empty list while the domain remains offline.
    """
    logger.info(f"Fetching Skillenza: {SKILLEZA_URL}")

    html = ""
    for fetcher in (_fetch_with_httpx, _fetch_with_browser):
        try:
            html = fetcher()
        except Exception as e:
            logger.error(f"Skillenza fetcher {fetcher.__name__} failed: {e}")
            html = ""
        if html:
            break

    if not html:
        logger.warning(
            "Skillenza is unreachable (platform shut down; skillenza.com "
            "expired in 2025) — returning no items"
        )
        return []

    items = _parse_listing(html)
    logger.info(f"Skillenza: scraped {len(items)} challenges")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_skillenza()
    for item in results:
        print(f"  {item.title} | {item.deadline or 'TBA'} | {item.link}")
