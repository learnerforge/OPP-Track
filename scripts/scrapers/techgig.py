"""
TechGig contest/challenge scraper (Times of India group).
The /challenge page server-renders only "Past Challenges"; live contests are
injected client-side, so this scraper tries two methods:
  1. httpx against https://www.techgig.com/challenge (kept for when TechGig
     starts server-rendering the live block again)
  2. scrapling StealthyFetcher (headless browser) as fallback — required today
Cards are parsed structurally from a.challenge-card elements carrying a
data-quiz-state attribute ("live" / "past"); only live contests are kept.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

TECHGIG_URL = "https://www.techgig.com/challenge"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _text(el) -> str:
    """Clean element text; TechGig markup contains literal '\\n' sequences."""
    return clean_text(str(el.text or "").replace("\\n", " "))


def _parse_card(card) -> ScrapeItem | None:
    """Parse one challenge card into a ScrapeItem."""
    href = card.attrib.get("href", "")
    state = card.attrib.get("data-quiz-state", "")
    if not href or state != "live":
        return None

    title_els = card.css("h4")
    title = _text(title_els[0]) if title_els else ""
    if not title:
        return None

    # Date range spans: first is start, last is end ("31 Mar" style, no year)
    date_texts = [_text(el) for el in card.css(".quiz-card__date_text") if _text(el)]
    deadline = ""
    if date_texts:
        deadline = parse_deadline(date_texts[-1])

    prize = ""
    price_els = card.css(".quiz-card__price_tag_text")
    if price_els:
        raw = _text(price_els[0])
        if raw:
            prize = f"₹{raw}" if raw.isdigit() else raw

    tags = [_text(el) for el in card.css("span.quiz__skill") if _text(el)]

    participants = ""
    count_els = card.css(".current_users_count b")
    if count_els:
        participants = _text(count_els[0])

    badge = ""
    badge_els = card.css(".badge_label_text")
    if badge_els:
        badge = _text(badge_els[0])

    notes_parts = ["Source: TechGig."]
    if badge:
        notes_parts.append(f"Status: {badge}.")
    if len(date_texts) > 1:
        notes_parts.append(f"Runs {date_texts[0]} – {date_texts[-1]}.")

    return ScrapeItem(
        title=title,
        type="Competition",
        source="TechGig",
        link=href,
        deadline=deadline,
        eligibility="Open to all",
        tags=tags or ["contest"],
        notes=" ".join(notes_parts),
        location="Online",
        prize_pool=prize,
        participants=participants,
    )


def _parse_listing(html: str) -> list[ScrapeItem]:
    """Extract all live challenge cards from a listings page."""
    from scrapling import Selector

    page = Selector(html)
    items: list[ScrapeItem] = []
    skipped_past = 0
    for card in page.css("a.challenge-card"):
        if card.attrib.get("data-quiz-state", "") != "live":
            skipped_past += 1
            continue
        try:
            item = _parse_card(card)
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
            f"  Found: {item.title} | {item.deadline or 'ongoing'} | "
            f"{item.prize_pool or '-'} | {item.link}"
        )
    if skipped_past:
        logger.info(f"  Skipped {skipped_past} past challenges")
    return items


def _fetch_with_httpx() -> str:
    """Fetch the challenge page with plain httpx. Returns HTML or ''."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = httpx.get(
        TECHGIG_URL, headers=headers, timeout=30, follow_redirects=True
    )
    if resp.status_code != 200:
        logger.warning(f"TechGig httpx returned status {resp.status_code}")
        return ""
    if 'data-quiz-state="live"' not in resp.text:
        logger.warning("TechGig httpx HTML has no live contests (JS-rendered)")
        return ""
    return resp.text


def _fetch_with_browser() -> str:
    """Fetch the challenge page with a stealth headless browser."""
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        logger.warning("scrapling not installed — browser fallback unavailable")
        return ""

    page = StealthyFetcher.fetch(
        TECHGIG_URL,
        headless=True,
        network_idle=True,
        timeout=30000,
    )
    if page.status != 200:
        logger.warning(f"TechGig browser fetch returned status {page.status}")
        return ""
    return str(page.body or "")


def scrape_techgig() -> list[ScrapeItem]:
    """Scrape live contests from the TechGig challenge listing page."""
    logger.info(f"Fetching TechGig: {TECHGIG_URL}")

    html = ""
    for fetcher in (_fetch_with_httpx, _fetch_with_browser):
        try:
            html = fetcher()
        except Exception as e:
            logger.error(f"TechGig fetcher {fetcher.__name__} failed: {e}")
            html = ""
        if html:
            break

    if not html:
        logger.error("TechGig: all fetch methods failed")
        return []

    items = deduplicate_by_link(_parse_listing(html))
    logger.info(f"TechGig: scraped {len(items)} live contests")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_techgig()
    for item in results:
        print(
            f"  {item.title} | {item.deadline or 'ongoing'} | "
            f"{item.prize_pool or '-'} | {item.link}"
        )
