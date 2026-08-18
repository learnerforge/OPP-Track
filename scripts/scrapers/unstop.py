"""
Unstop hackathon and internship scraper.
Unstop requires cookies/JS — uses StealthyFetcher.
"""

from __future__ import annotations

import re
import logging
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

UNSTOP_URLS = [
    ("https://unstop.com/hackathons", "Hackathon"),
    ("https://unstop.com/internships", "Internship"),
    ("https://unstop.com/competitions", "Hackathon"),
]


def _extract_deadline(text: str) -> str:
    """Extract deadline from Unstop text like 'Registration closes 25 Aug 2026'."""
    if not text:
        return ""
    text_lower = text.lower()

    if any(w in text_lower for w in ("ended", "past", "closed")):
        return ""

    # "25 Aug 2026" or "Aug 25, 2026"
    match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', text)
    if match:
        return parse_deadline(match.group(1))
    match = re.search(r'(\w+\s+\d{1,2},?\s*\d{4})', text)
    if match:
        return parse_deadline(match.group(1))

    return ""


def _determine_type(title: str, hint: str) -> str:
    """Determine if it's a hackathon, internship, or certification."""
    title_lower = title.lower()
    if "intern" in title_lower or "internship" in title_lower:
        return "Internship"
    if "certif" in title_lower:
        return "Certification"
    if hint in ("Hackathon", "Internship"):
        return hint
    return "Hackathon"


def scrape_unstop() -> list[ScrapeItem]:
    """Scrape hackathons and internships from Unstop."""
    items: list[ScrapeItem] = []

    for url, hint_type in UNSTOP_URLS:
        logger.info(f"Fetching Unstop: {url}")
        try:
            page = StealthyFetcher.fetch(
                url,
                headless=True,
                disable_resources=True,
                network_idle=True,
                timeout=30000,
            )

            if page.status != 200:
                logger.warning(f"Unstop returned status {page.status} for {url}")
                continue

            # Unstop uses card-based layouts. Try multiple selectors.
            cards = (
                page.css('[class*="card"]') or
                page.css('[class*="Card"]') or
                page.css('[class*="listing"]') or
                page.css('[class*="Listing"]') or
                page.css('[class*="event"]') or
                page.css('[class*="Event"]')
            )

            seen_titles: set[str] = set()
            for card in cards:
                # Get title
                title_el = (
                    card.css("h2::text") or card.css("h3::text") or
                    card.css("h4::text") or card.css("a::text")
                )
                title = ""
                for el in title_el:
                    t = clean_text(el)
                    if t and len(t) > 3:
                        title = t
                        break
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                # Get link
                link_el = card.css("a[href]")
                link = ""
                for el in link_el:
                    href = el.attrib.get("href", "")
                    if href and ("/hackathon" in href or "/internship" in href or "/competition" in href or "/event" in href):
                        link = href if href.startswith("http") else f"https://unstop.com{href}"
                        break

                # Get deadline
                deadline = ""
                for el in card.css("*"):
                    text = clean_text(el.text)
                    if any(kw in text.lower() for kw in ("register", "deadline", "close", "start", "end")):
                        deadline = _extract_deadline(text)
                        if deadline:
                            break

                # Determine type
                opp_type = _determine_type(title, hint_type)

                if not link:
                    link = f"https://unstop.com/search?q={title.replace(' ', '+')}"

                item = ScrapeItem(
                    title=title,
                    type=opp_type,
                    source="Unstop",
                    link=link,
                    deadline=deadline,
                    eligibility="Check Unstop for eligibility details",
                    tags=[],
                    notes=f"Source: Unstop."
                )
                items.append(item)
                logger.info(f"  Found: {title} ({opp_type})")

        except Exception as e:
            logger.error(f"Error scraping Unstop {url}: {e}")

    logger.info(f"Unstop: scraped {len(items)} opportunities")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_unstop()
    for item in results:
        print(f"  {item.title} | {item.type} | {item.deadline} | {item.link}")
