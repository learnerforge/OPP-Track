"""
MachineHack competitions scraper.
machinehack.com is a client-side SPA, but the /competitions page
server-renders 'hover-card' anchors per competition containing title,
description, host and open/close dates. The legacy /hackathons path and the
homepage are tried as fallbacks since the site has been restructured before.
"""

from __future__ import annotations

import re
import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

MACHINEHACK_BASE = "https://machinehack.com"
MACHINEHACK_URLS = [
    f"{MACHINEHACK_BASE}/competitions",
    f"{MACHINEHACK_BASE}/hackathons",
    MACHINEHACK_BASE,
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Competition cards are <a href="/competitions/{slug}" class="... hover-card ...">
CARD_RE = re.compile(
    r'<a\s+href="(/competitions/[^"#?]+)"([^>]*)>(.*?)</a>', re.DOTALL
)
TITLE_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.DOTALL)
DESC_RE = re.compile(r'<p class="[^"]*text-muted-foreground[^"]*"[^>]*>(.*?)</p>', re.DOTALL)
SPAN_RE = re.compile(r"<span(?:\s[^>]*)?>(.*?)</span>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
COMMENT_RE = re.compile(r"<!--.*?-->")
DATE_IN_TEXT_RE = re.compile(r"\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}")


def _clean_fragment(fragment: str) -> str:
    """Strip tags/comments and collapse whitespace from an HTML fragment."""
    text = COMMENT_RE.sub(" ", fragment)
    text = TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_date(text: str) -> str:
    """Pull a concrete date out of text like 'Closes: 27 Sep 2026, 23:59 IST'."""
    match = DATE_IN_TEXT_RE.search(text)
    if not match:
        return ""
    return parse_deadline(match.group(0))


def _parse_card(slug: str, attrs: str, body: str) -> ScrapeItem | None:
    """Parse one hover-card anchor into a ScrapeItem."""
    if "hover-card" not in attrs:
        return None

    title_match = TITLE_RE.search(body)
    title = clean_text(title_match.group(1)) if title_match else ""
    if not title:
        return None

    description = ""
    desc_match = DESC_RE.search(body)
    if desc_match:
        description = _clean_fragment(desc_match.group(1))

    organizer = ""
    deadline = ""
    opens = ""
    extra_status = ""
    for raw in SPAN_RE.findall(body):
        text = _clean_fragment(raw)
        if not text:
            continue
        lower = text.lower()
        if lower.startswith("host:"):
            organizer = text.split(":", 1)[1].strip()
        elif lower.startswith("closes:"):
            deadline = _extract_date(text)
        elif lower.startswith("ends:"):
            deadline = _extract_date(text)
        elif lower.startswith("opens:"):
            opens = _extract_date(text)
        elif not extra_status:
            extra_status = text

    if not deadline and opens:
        deadline = opens

    notes_parts = ["Source: MachineHack."]
    if description:
        notes_parts.append(description[:200])
    if extra_status:
        notes_parts.append(extra_status)

    return ScrapeItem(
        title=title,
        type="Competition",
        source="MachineHack",
        link=f"{MACHINEHACK_BASE}{slug}",
        deadline=deadline,
        eligibility="Open to all",
        tags=["machine learning", "ai", "prediction"],
        location="Online",
        organizer=organizer,
        notes=" ".join(notes_parts),
    )


def _parse_listings_html(html: str) -> list[ScrapeItem]:
    """Extract all competition hover-cards from a MachineHack page."""
    items: list[ScrapeItem] = []
    seen_slugs: set[str] = set()
    for match in CARD_RE.finditer(html):
        slug, attrs, body = match.groups()
        # Skip detail-page sub-links (footer nav) — real cards have no suffix
        if slug.count("/") != 2 or slug in seen_slugs:
            continue
        item = _parse_card(slug, attrs, body)
        if not item:
            continue
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        seen_slugs.add(slug)
        items.append(item)
        logger.info(
            f"  Found: {item.title} | {item.deadline or 'no deadline'} | "
            f"{item.organizer or '-'}"
        )
    return items


def scrape_machinehack() -> list[ScrapeItem]:
    """Scrape active competitions from MachineHack."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for url in MACHINEHACK_URLS:
        items: list[ScrapeItem] = []
        logger.info(f"Fetching MachineHack: {url}")
        try:
            resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        except Exception as e:
            logger.error(f"Error fetching MachineHack {url}: {e}")
            continue

        if resp.status_code != 200:
            logger.warning(f"MachineHack returned status {resp.status_code} for {url}")
            continue

        try:
            items = _parse_listings_html(resp.text)
        except Exception as e:
            logger.error(f"Error parsing MachineHack {url}: {e}")
            continue

        if items:
            logger.info(f"MachineHack: scraped {len(items)} competitions from {url}")
            return items
        logger.warning(f"MachineHack: no competition cards found at {url}")

    logger.error("MachineHack: all URLs exhausted without results")
    return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_machinehack()
    for item in results:
        print(
            f"  {item.title} | {item.deadline or 'ongoing'} | "
            f"{item.organizer or '-'} | {item.link}"
        )
