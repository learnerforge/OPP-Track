"""
Devpost hackathon scraper.
Devpost is a React SPA — needs StealthyFetcher for JS rendering.
"""

from __future__ import annotations

import re
import logging
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

DEVPOST_URLS = [
    "https://devpost.com/hackathons?status[]=upcoming",
    "https://devpost.com/hackathons?status[]=open",
]


def _extract_deadline_from_text(text: str) -> str:
    """Extract deadline from text like 'Oct 15, 2026 at 11:59pm EDT'."""
    if not text:
        return ""
    # "Oct 15, 2026"
    match = re.search(r'(\w+ \d{1,2},?\s*\d{4})', text)
    if match:
        return parse_deadline(match.group(1))
    # "2026-10-15"
    match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    if match:
        return match.group(1)
    return ""


def scrape_devpost() -> list[ScrapeItem]:
    """Scrape upcoming and open hackathons from Devpost."""
    items: list[ScrapeItem] = []

    for url in DEVPOST_URLS:
        logger.info(f"Fetching Devpost: {url}")
        try:
            page = StealthyFetcher.fetch(
                url,
                headless=True,
                disable_resources=True,
                network_idle=True,
                timeout=30000,
            )

            if page.status != 200:
                logger.warning(f"Devpost returned status {page.status} for {url}")
                continue

            # Devpost hackathon cards are typically in divs with specific classes
            # Each card has: title link, deadline text, sponsor/organizer info
            cards = page.css('.hackathon-tile') or page.css('[class*="hackathon"]') or page.css('.small-12.columns')

            if not cards:
                # Fallback: look for links to hackathon pages
                links = page.css('a[href*="/hackathons/"]')
                seen: set[str] = set()
                for link in links:
                    href = link.attrib.get("href", "")
                    if not href or "/hackathons/" not in href or href in seen:
                        continue
                    if href == "/hackathons" or href.endswith("/hackathons/") or "?" in href:
                        continue
                    seen.add(href)

                    title = clean_text(link.text)
                    if not title or len(title) < 5:
                        continue

                    # Skip navigation links
                    if title.lower() in ("hackathons", "browse hackathons", "projects", "explore projects"):
                        continue

                    full_url = href if href.startswith("http") else f"https://devpost.com{href}"

                    # Try to find deadline near this element
                    parent = link.parent
                    deadline_text = ""
                    if parent:
                        parent_text = parent.text or ""
                        deadline_text = _extract_deadline_from_text(parent_text)

                    item = ScrapeItem(
                        title=title,
                        type="Hackathon",
                        source="Devpost",
                        link=full_url,
                        deadline=deadline_text,
                        eligibility="Open to all developers",
                        tags=[],
                        notes=f"Source: Devpost."
                    )
                    items.append(item)
                    logger.info(f"  Found: {title}")

            else:
                for card in cards:
                    # Get title
                    title_el = card.css("h3::text") or card.css("h2::text") or card.css("a::text")
                    title = clean_text(title_el[0] if title_el else "")
                    if not title or len(title) < 5:
                        continue

                    # Get link
                    link_el = card.css("a[href*='/hackathons/']")
                    link = ""
                    if link_el:
                        href = link_el[0].attrib.get("href", "")
                        link = href if href.startswith("http") else f"https://devpost.com{href}"

                    # Get deadline
                    deadline_text = ""
                    for el in card.css("*"):
                        text = clean_text(el.text)
                        if "deadline" in text.lower() or any(month in text.lower() for month in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]):
                            deadline_text = _extract_deadline_from_text(text)
                            if deadline_text:
                                break

                    if not link:
                        continue

                    item = ScrapeItem(
                        title=title,
                        type="Hackathon",
                        source="Devpost",
                        link=link,
                        deadline=deadline_text,
                        eligibility="Open to all developers",
                        tags=[],
                        notes=f"Source: Devpost."
                    )
                    items.append(item)
                    logger.info(f"  Found: {title}")

        except Exception as e:
            logger.error(f"Error scraping Devpost {url}: {e}")

    logger.info(f"Devpost: scraped {len(items)} hackathons")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_devpost()
    for item in results:
        print(f"  {item.title} | {item.deadline} | {item.link}")
