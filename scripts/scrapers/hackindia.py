"""
HackIndia hackathon events scraper (hackindia.org).
The site is a client-rendered Next.js app — plain httpx returns an app shell
with no event links, so this scraper tries two methods:
  1. httpx against https://hackindia.org/events (redirects to /hackathons;
     detected as useless when no /<year>/<slug> links are present)
  2. scrapling StealthyFetcher (headless browser) as fallback
Event cards are <article class="group ..."> elements carrying location, title,
prize, builder count, status and tag chips; the featured hero banner is parsed
separately. The listing shows no dates, so deadlines are left empty.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from urllib.parse import urljoin

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, parse_deadline, deduplicate_by_link

logger = logging.getLogger(__name__)

HACKINDIA_URL = "https://hackindia.org/events"

# Registration states published on each event card.
OPEN_STATUSES = {"REGISTERING", "UPCOMING", "LIVE", "OPEN", "REGISTRATION OPEN"}
ENDED_STATUSES = {"CLOSED", "ENDED", "FINISHED", "COMPLETED", "PAST", "ANNOUNCED"}

# Detail pages embed a schema.org Event JSON-LD block with start/end dates.
JSONLD_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _extract_status(article) -> str:
    """Read the registration-status label from an event card.

    Cards carry a short uppercase status chip such as 'REGISTERING',
    'UPCOMING', 'CLOSED' or 'ENDED'. It lives in one of the small muted
    paragraphs, distinct from the location (first) and 'Prize'/'Builders'
    labels.
    """
    status = ""
    for p in article.css("p"):
        text = clean_text(p.text).strip()
        if not text:
            continue
        upper = text.upper()
        if upper in OPEN_STATUSES or upper in ENDED_STATUSES:
            return upper
    return status


def _is_past_year_path(link: str) -> bool:
    """True if the event path is an archived year before the current year."""
    match = re.search(r"/hackindia\.org/(\d{4})/", link)
    if not match:
        return False
    try:
        return int(match.group(1)) < datetime.now().year
    except ValueError:
        return False


def _fetch_deadline(link: str) -> str:
    """Cheaply fetch a HackIndia detail page and read the event end date.

    Detail pages are server-rendered and carry a schema.org Event JSON-LD
    block (startDate/endDate), so a plain HTTP GET is enough — no browser.
    Returns 'YYYY-MM-DD' or '' when unavailable.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = httpx.get(link, headers=headers, timeout=20, follow_redirects=True)
        if resp.status_code != 200:
            return ""
        matches = JSONLD_RE.findall(resp.text)
        for raw in matches:
            try:
                node = json.loads(raw.strip())
            except (json.JSONDecodeError, ValueError):
                continue
            nodes = node if isinstance(node, list) else [node]
            for entry in nodes:
                if isinstance(entry, dict) and entry.get("@type") == "Event":
                    end = entry.get("endDate") or ""
                    if end:
                        parsed = parse_deadline(end.split("T")[0])
                        if parsed:
                            return parsed
    except Exception as e:
        logger.debug(f"  HackIndia deadline fetch error for {link}: {e}")
    return ""


def _parse_article(article) -> ScrapeItem | None:
    """Parse one event card into a ScrapeItem."""
    title_els = article.css("h3 a[href]")
    if not title_els:
        return None
    title = clean_text(title_els[0].text)
    href = title_els[0].attrib.get("href", "")
    if not title or not href:
        return None
    link = urljoin("https://hackindia.org/", href)

    # First small uppercase paragraph is the location ("Virtual" / city)
    location = ""
    for p in article.css("p"):
        classes = p.attrib.get("class", "")
        p_text = clean_text(p.text)
        if "uppercase" in classes and p_text:
            location = p_text
            break

    # Orange paragraph is the prize ("TBA" or an amount)
    prize = ""
    for p in article.css("p"):
        if "text-orange-600" in p.attrib.get("class", ""):
            raw = clean_text(p.text)
            if raw and raw.upper() != "TBA":
                prize = raw
            break

    participants = ""
    status = _extract_status(article)
    for p in article.css("p"):
        p_text = clean_text(p.text)
        p_lower = p_text.lower()
        if not p_text:
            continue
        if "builders" in p_lower or "participants" in p_lower:
            participants = p_text.split()[0] if p_text.split() else ""

    tags = [
        clean_text(el.text)
        for el in article.css("span")
        if clean_text(el.text) and len(clean_text(el.text)) < 30
    ]

    notes_parts = ["Source: HackIndia."]
    if status:
        notes_parts.append(f"Status: {status}.")
    if prize:
        notes_parts.append(f"Prize: {prize}.")

    return ScrapeItem(
        title=title,
        type="Hackathon",
        source="HackIndia",
        link=link,
        deadline="",
        eligibility="Open to college students and developers",
        tags=tags or ["hackathon"],
        notes=" ".join(notes_parts),
        location=location,
        prize_pool=prize,
        participants=participants,
    )


def _parse_hero(page) -> ScrapeItem | None:
    """Parse the featured hero banner at the top of the listing."""
    sections = page.css('section[class*="bg-orange-600"]')
    if not sections:
        return None
    section = sections[0]

    title_els = section.css("h2 a[href]")
    if not title_els:
        return None
    title = clean_text(title_els[0].text)
    href = title_els[0].attrib.get("href", "")
    if not title or not href:
        return None

    # Metric blocks: big bold value followed by a label ("Prize Pool"/"Builders")
    prize = ""
    participants = ""
    all_text_ps = section.css("p")
    for i, p in enumerate(all_text_ps):
        p_text = clean_text(p.text)
        label = (
            clean_text(all_text_ps[i + 1].text).lower()
            if i + 1 < len(all_text_ps)
            else ""
        )
        if not p_text:
            continue
        if label.startswith("prize") and p_text.upper() != "TBA":
            prize = p_text
        elif label.startswith("builder"):
            participants = p_text

    notes_parts = ["Source: HackIndia.", "Featured event."]
    if prize:
        notes_parts.append(f"Prize: {prize}.")

    return ScrapeItem(
        title=title,
        type="Hackathon",
        source="HackIndia",
        link=urljoin("https://hackindia.org/", href),
        deadline="",
        eligibility="Open to college students and developers",
        tags=["hackathon"],
        notes=" ".join(notes_parts),
        prize_pool=prize,
        participants=participants,
    )


def _parse_listing(html: str) -> list[ScrapeItem]:
    """Extract the hero banner plus all event cards from a rendered page."""
    from scrapling import Selector

    page = Selector(html)
    items: list[ScrapeItem] = []
    skipped_past = 0

    try:
        hero = _parse_hero(page)
    except Exception as e:
        logger.debug(f"  Hero parse error: {e}")
        hero = None
    if hero:
        errors = hero.validate()
        if not errors and not _is_past_year_path(hero.link):
            items.append(hero)
            logger.info(f"  Found (featured): {hero.title} | {hero.link}")

    for article in page.css("article.group"):
        try:
            item = _parse_article(article)
            status = _extract_status(article)
        except Exception as e:
            logger.debug(f"  Card parse error: {e}")
            continue
        if not item:
            continue
        # Keep only current / upcoming events: drop explicitly-ended ones and
        # archived events from previous years.
        if status in ENDED_STATUSES:
            skipped_past += 1
            continue
        if _is_past_year_path(item.link):
            skipped_past += 1
            continue
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue

        deadline = _fetch_deadline(item.link)
        if deadline:
            item.deadline = deadline
        items.append(item)
        logger.info(
            f"  Found: {item.title} | {item.location or '-'} | "
            f"deadline={item.deadline or '-'} | {item.link}"
        )
    if skipped_past:
        logger.info(f"  Skipped {skipped_past} ended/closed/archived events")
    return items


def _fetch_with_httpx() -> str:
    """Fetch the events page with plain httpx. Returns HTML or ''."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = httpx.get(
        HACKINDIA_URL, headers=headers, timeout=30, follow_redirects=True
    )
    if resp.status_code != 200:
        logger.warning(f"HackIndia httpx returned status {resp.status_code}")
        return ""
    if "/2026/" not in resp.text and "/2025/" not in resp.text:
        logger.warning("HackIndia httpx got the JS app shell (no event links)")
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
        HACKINDIA_URL,
        headless=True,
        network_idle=True,
        timeout=30000,
    )
    if page.status != 200:
        logger.warning(f"HackIndia browser fetch returned status {page.status}")
        return ""
    return str(page.body or "")


def scrape_hackindia() -> list[ScrapeItem]:
    """Scrape hackathon events from the HackIndia listing page."""
    logger.info(f"Fetching HackIndia: {HACKINDIA_URL}")

    html = ""
    for fetcher in (_fetch_with_httpx, _fetch_with_browser):
        try:
            html = fetcher()
        except Exception as e:
            logger.error(f"HackIndia fetcher {fetcher.__name__} failed: {e}")
            html = ""
        if html:
            break

    if not html:
        logger.error("HackIndia: all fetch methods failed")
        return []

    items = deduplicate_by_link(_parse_listing(html))
    logger.info(f"HackIndia: scraped {len(items)} events")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackindia()
    for item in results:
        print(
            f"  {item.title} | {item.location or '-'} | "
            f"{item.prize_pool or '-'} | {item.link}"
        )
