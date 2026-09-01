"""
MachineHack scraper.
machinehack.com is a client-side SPA; the /competitions page (Next.js RSC)
requires JS rendering. Each competition is a card with an <h2> title, host,
opens/closes dates, prizes, and a link to /competitions/{slug}.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

MACHINEHACK_BASE = "https://machinehack.com"
MACHINEHACK_URL = f"{MACHINEHACK_BASE}/competitions"

FETCH_ARGS = {
    "headless": True,
    "network_idle": True,
    "timeout": 45000,
}

TAG_RE = re.compile(r"<[^>]+>")

# Match a calendar date like "20 Aug 2026" or "27 Sep 2026"
CALENDAR_DATE_RE = re.compile(r"\b\d{1,2}\s+\w{3,9}\s+\d{4}\b")


def _parse_date(text: str) -> str:
    """Extract and parse the first calendar date from a raw field value."""
    m = CALENDAR_DATE_RE.search(text)
    if not m:
        return ""
    return parse_deadline(m.group(0))


def _clean(html: str) -> str:
    """Strip tags but keep whitespace/newlines that separate fields."""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


def _extract(label: str, text: str) -> str:
    """Extract the value following a label like 'Closes' from card text.

    Fields usually appear as 'Host AIM Media House' or 'Closes 27 Sep 2026'.
    We find the label token and take the text until the next known label or
    a date that clearly starts the next field.
    """
    known = [
        "Host", "Opens", "Closes", "Prizes", "Timeline", "Register now",
        "View competition", "Registration opens", "Featured competition",
    ]
    # Build a token-searchable copy preserving case
    pos = text.find(label)
    if pos < 0:
        return ""
    rest = text[pos + len(label):].strip()
    # Cut at the next known label (case-insensitive, word boundary)
    best = len(rest) + 1
    lower_rest = rest.lower()
    for k in known:
        if k.lower() == label.lower():
            continue
        idx = lower_rest.find(k.lower())
        if idx >= 0 and idx < best:
            best = idx
    return rest[:best].strip()


def scrape_machinehack() -> list[ScrapeItem]:
    """Scrape active hackathons from MachineHack."""
    items: list[ScrapeItem] = []
    logger.info("Fetching MachineHack: %s", MACHINEHACK_URL)

    try:
        page = StealthyFetcher.fetch(MACHINEHACK_URL, **FETCH_ARGS)
    except Exception as e:
        logger.error("MachineHack fetch failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("MachineHack returned %d", page.status)
        return items

    body = page.body.decode("utf-8", "replace")

    # Split body into card blocks. Cards start after an <h2> title.
    # Use h2 as card marker and take the following content until the next h2.
    h2_matches = list(re.finditer(r"<h2[^>]*>(.*?)</h2>", body, re.DOTALL))
    seen_slugs = set()

    for i, m in enumerate(h2_matches):
        title = clean_text(m.group(1))
        if not title or len(title) < 3 or title.lower() in ("competitions",):
            continue
        # Card content = between this h2 and the next h2
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(body)
        card_html = body[m.end():end]
        card_text = _clean(card_html)
        if not card_text:
            continue

        # Detail link within this card
        link_m = re.search(r'href="(/competitions/[a-z0-9][a-z0-9-]*)"', card_html)
        if not link_m:
            continue
        slug = link_m.group(1)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        full_url = urljoin(MACHINEHACK_BASE, slug)

        # Dates: "Opens 20 Aug 2026" / "Closes 27 Sep 2026, 23:59 IST"
        opens_raw = _extract("Opens", card_text)
        closes_raw = _extract("Closes", card_text)
        deadline = _parse_date(closes_raw) or _parse_date(opens_raw)

        # Host and prizes
        host = _extract("Host", card_text)
        prize = _extract("Prizes", card_text)[:120]

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="MachineHack",
            link=full_url,
            deadline=deadline,
            eligibility="Open to all",
            tags=["machine learning", "ai", "prediction"],
            location="Online",
            organizer=host,
            prize_pool=prize,
            notes="Source: MachineHack.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("MachineHack: scraped %d competitions", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_machinehack()
    print(f"MachineHack: {len(results)} items")
    for item in results:
        print(f"  {item.title} | {item.deadline} | {item.organizer} | {item.link}")
