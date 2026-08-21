"""
Kaggle competitions scraper.
The public API (api/v1) requires auth and www.kaggle.com serves a reCAPTCHA
challenge to plain HTTP clients, so this scraper tries two methods:
  1. httpx against https://www.kaggle.com/competitions (works when Kaggle
     serves the server-rendered page instead of the challenge)
  2. scrapling StealthyFetcher (headless browser) as fallback
Competition cards are parsed structurally from role="listitem" elements —
Kaggle uses unstable styled-components class names, so no CSS classes are
relied upon.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime, timedelta

import httpx

from scripts.scrapers.base import ScrapeItem, deduplicate

logger = logging.getLogger(__name__)

KAGGLE_COMPETITIONS_URL = "https://www.kaggle.com/competitions"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

LISTITEM_SPLIT_RE = re.compile(r'<div role="listitem"', re.IGNORECASE)
ARIA_LABEL_RE = re.compile(r'aria-label="([^"]*)"')
HREF_RE = re.compile(r'href="(/competitions/[^"#?]+)"')
TEAMS_RE = re.compile(r">([\d,]+)\s+Teams<")
PRIZE_RE = re.compile(r"<h2[^>]*>(\$[\d,.]+(?:\s*[KMB])?)</h2>", re.IGNORECASE)
SPAN_RE = re.compile(r"<span(?:\s[^>]*)?>([^<>]+)</span>")
TAG_RE = re.compile(r"<[^>]+>")


def _is_challenge_page(html: str) -> bool:
    """Detect Google reCAPTCHA challenge shells served instead of the real page."""
    head = html[:5000].lower()
    return "recaptcha" in head or "challengepage" in head


def _relative_time_to_deadline(text: str) -> str:
    """Convert Kaggle countdown text ('24 days to go', 'A month to go',
    '7 hours to go') into an approximate YYYY-MM-DD date."""
    text_lower = text.lower().strip()
    now = datetime.now()

    match = re.search(r"(\d+)\s+day", text_lower)
    if match:
        return (now + timedelta(days=int(match.group(1)))).strftime("%Y-%m-%d")

    # 'A month to go' / '3 months to go' — approximate a month as 30 days
    months = 1 if re.search(r"\ba\s+month\b", text_lower) else None
    if months is None:
        m = re.search(r"(\d+)\s+month", text_lower)
        months = int(m.group(1)) if m else None
    if months:
        return (now + timedelta(days=30 * months)).strftime("%Y-%m-%d")

    match = re.search(r"(\d+)\s+hour", text_lower)
    if match:
        return now.strftime("%Y-%m-%d")

    return ""


def _clean_fragment(fragment: str) -> str:
    """Strip tags/comments and collapse whitespace from an HTML fragment."""
    text = re.sub(r"<!--.*?-->", " ", fragment, flags=re.DOTALL)
    text = TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _unescape_utf8(text: str) -> str:
    """Kaggle sometimes emits raw UTF-8 as literal '\\xc3\\xa9'-style escapes."""
    if "\\x" not in text:
        return text
    try:
        return (
            text.encode("utf-8")
            .decode("unicode_escape")
            .encode("latin-1")
            .decode("utf-8", errors="replace")
        )
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def _parse_card(card_html: str) -> ScrapeItem | None:
    """Parse one role='listitem' competition card into a ScrapeItem."""
    label_match = ARIA_LABEL_RE.search(card_html)
    href_match = HREF_RE.search(card_html)
    if not href_match:
        return None

    title = (label_match.group(1) if label_match else "").strip()
    slug = href_match.group(1)
    if not title:
        # Fall back to the visible title div inside the anchor
        anchor = card_html.split("</a>", 1)[0]
        titles = re.findall(r">([^<>]{8,120})</div>", anchor)
        title = titles[0].strip() if titles else ""
    title = _unescape_utf8(title)
    if not title:
        return None

    # Teams/participants live inside the anchor; prize & countdown after it
    anchor_part, _, tail_part = card_html.partition("</a>")

    teams_match = TEAMS_RE.search(anchor_part)
    participants = teams_match.group(1).replace(",", "") if teams_match else ""

    prize = ""
    prize_match = PRIZE_RE.search(tail_part)
    if prize_match:
        prize = prize_match.group(1).replace(" ", "")

    # First meaningful tail span is the status/countdown for THIS card
    # (later spans belong to unrelated page sections)
    deadline = ""
    status = ""
    for raw in SPAN_RE.findall(tail_part):
        text = _clean_fragment(raw)
        if not text or text == "info":
            continue
        status = text
        break

    if status:
        if status.lower() == "ongoing":
            deadline = ""
        else:
            deadline = _relative_time_to_deadline(status)

    notes_parts = ["Source: Kaggle."]
    if status:
        suffix = " (approx)" if deadline else ""
        notes_parts.append(f"Status: {status}{suffix}.")
    if prize:
        notes_parts.append(f"Prize: {prize}.")

    return ScrapeItem(
        title=title,
        type="Competition",
        source="Kaggle",
        link=f"https://www.kaggle.com{slug}",
        deadline=deadline,
        eligibility="Open to all",
        tags=["machine learning", "data science", "competition"],
        location="Online",
        prize_pool=prize,
        participants=participants,
        notes=" ".join(notes_parts),
    )


def _parse_competitions_html(html: str) -> list[ScrapeItem]:
    """Extract all competition cards from a Kaggle listings page."""
    items: list[ScrapeItem] = []
    cards = LISTITEM_SPLIT_RE.split(html)[1:]
    for card_html in cards:
        # Cut at the next major section boundary to avoid bleeding noise
        item = _parse_card(card_html)
        if not item:
            continue
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        items.append(item)
        logger.info(
            f"  Found: {item.title} | {item.deadline or 'ongoing'} | "
            f"prize={item.prize_pool or '-'} | teams={item.participants or '-'}"
        )
    return items


def _fetch_with_httpx() -> str:
    """Fetch the competitions page with plain httpx. Returns HTML or ''."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = httpx.get(
        KAGGLE_COMPETITIONS_URL, headers=headers, timeout=30, follow_redirects=True
    )
    if resp.status_code != 200:
        logger.warning(f"Kaggle httpx returned status {resp.status_code}")
        return ""
    if _is_challenge_page(resp.text):
        logger.warning("Kaggle httpx hit a reCAPTCHA challenge page")
        return ""
    return resp.text


def _fetch_with_browser() -> str:
    """Fetch the competitions page with a stealth headless browser."""
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        logger.warning("scrapling not installed — browser fallback unavailable")
        return ""

    page = StealthyFetcher.fetch(
        KAGGLE_COMPETITIONS_URL,
        headless=True,
        disable_resources=True,
        network_idle=True,
        timeout=60000,
    )
    if page.status != 200:
        logger.warning(f"Kaggle browser fetch returned status {page.status}")
        return ""
    return str(page.body or "")


def scrape_kaggle() -> list[ScrapeItem]:
    """Scrape active competitions from the Kaggle competitions listing page."""
    logger.info(f"Fetching Kaggle: {KAGGLE_COMPETITIONS_URL}")

    html = ""
    for fetcher in (_fetch_with_httpx, _fetch_with_browser):
        try:
            html = fetcher()
        except Exception as e:
            logger.error(f"Kaggle fetcher {fetcher.__name__} failed: {e}")
            html = ""
        if html:
            break

    if not html:
        logger.error("Kaggle: all fetch methods failed")
        return []

    items = deduplicate(_parse_competitions_html(html))
    logger.info(f"Kaggle: scraped {len(items)} competitions")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_kaggle()
    for item in results:
        print(
            f"  {item.title} | {item.deadline or 'ongoing'} | "
            f"{item.prize_pool or '-'} | {item.participants or '-'} teams | {item.link}"
        )
