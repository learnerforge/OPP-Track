"""
Devfolio hackathon scraper.
Devfolio renders via Next.js SSR — content is available in the initial HTML.
"""

from __future__ import annotations

import re
import logging
from scrapling.fetchers import Fetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

DEVFOLIO_BASE = "https://devfolio.co"
DEVFOLIO_OPEN = f"{DEVFOLIO_BASE}/hackathons/open"
DEVFOLIO_UPCOMING = f"{DEVFOLIO_BASE}/hackathons/upcoming"


def _extract_deadline_from_text(text: str) -> str:
    """Extract deadline from Devfolio card text like 'Starts 25/08/26' or 'Live'."""
    if not text:
        return ""
    text_lower = text.lower().strip()

    if text_lower in ("live", "open", "ended"):
        return ""

    # "Starts 25/08/26" or "Starts 25/08/2026"
    match = re.search(r'starts?\s+(\d{1,2}/\d{1,2}/\d{2,4})', text_lower)
    if match:
        date_str = match.group(1)
        parts = date_str.split("/")
        if len(parts) == 3:
            day, month, year = parts
            if len(year) == 2:
                year = "20" + year
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # "Aug 15, 2026" style
    match = re.search(r'(\w+ \d{1,2},?\s*\d{4})', text)
    if match:
        return parse_deadline(match.group(1))

    return ""


def _extract_theme(tag_elements) -> list[str]:
    """Extract theme tags from Devfolio card elements."""
    themes = []
    for el in tag_elements:
        text = clean_text(el.text)
        if text and text.lower() not in ("hackathon", "online", "offline"):
            themes.append(text)
    return themes


def scrape_devfolio() -> list[ScrapeItem]:
    """Scrape open and upcoming hackathons from Devfolio."""
    items: list[ScrapeItem] = []
    urls = [DEVFOLIO_OPEN, DEVFOLIO_UPCOMING]

    for url in urls:
        logger.info(f"Fetching Devfolio: {url}")
        try:
            page = Fetcher.get(url, impersonate="chrome")
            if page.status != 200:
                logger.warning(f"Devfolio returned status {page.status} for {url}")
                continue

            # Devfolio uses card-based layout. Each hackathon card has:
            # - A link with href containing the hackathon slug
            # - Title in an h3 or similar heading
            # - Theme tags
            # - Status indicators (Open, Ended, etc.)
            cards = page.css('a[href*=".devfolio.co"]')

            seen_urls: set[str] = set()
            for card in cards:
                href = card.attrib.get("href", "")
                if not href or not href.endswith(".devfolio.co"):
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # Get title from the card's heading
                title_el = card.css("h3::text") or card.css("h2::text")
                title = clean_text(title_el[0] if title_el else card.text)
                if not title or len(title) < 3:
                    continue

                # Skip generic navigation links
                if title.lower() in ("open", "upcoming", "past", "all open hackathons", "all upcoming hackathons"):
                    continue

                # Get status text from the card
                status_els = card.css("span::text") or card.css("p::text")
                status_text = " ".join(clean_text(s) for s in status_els)

                # Skip ended hackathons
                if "ended" in status_text.lower() or "see projects" in status_text.lower():
                    continue

                # Extract themes
                themes = []
                for span in card.css("span"):
                    text = clean_text(span.text)
                    if text and text.lower() not in ("hackathon", "online", "offline", "ended", "open", "upcoming") and not text.startswith("+") and "participat" not in text.lower():
                        themes.append(text)

                # Extract deadline
                deadline = _extract_deadline_from_text(status_text)

                link = href if href.startswith("http") else f"{DEVFOLIO_BASE}{href}"

                item = ScrapeItem(
                    title=title,
                    type="Hackathon",
                    source="Devfolio",
                    link=link,
                    deadline=deadline,
                    eligibility="Open to all students and developers",
                    tags=themes[:5],
                    notes=f"Source: Devfolio. Status: {clean_text(status_text)}."
                )
                items.append(item)
                logger.info(f"  Found: {title}")

        except Exception as e:
            logger.error(f"Error scraping Devfolio {url}: {e}")

    logger.info(f"Devfolio: scraped {len(items)} hackathons")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_devfolio()
    for item in results:
        print(f"  {item.title} | {item.deadline} | {item.link}")
