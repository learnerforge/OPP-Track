"""
Internshala internship scraper.
Internshala is a heavy SPA — uses StealthyFetcher.
"""

from __future__ import annotations

import re
import logging
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

INTERNSHALA_URLS = [
    "https://internshala.com/internships",
    "https://internshala.com/internships/work-from-home-internships",
]


def _extract_stipend(text: str) -> str:
    """Extract stipend from text like '₹ 10,000 /month'."""
    if not text:
        return ""
    match = re.search(r'₹\s*[\d,]+', text)
    return match.group(0) if match else ""


def scrape_internshala() -> list[ScrapeItem]:
    """Scrape internships from Internshala."""
    items: list[ScrapeItem] = []

    for url in INTERNSHALA_URLS:
        logger.info(f"Fetching Internshala: {url}")
        try:
            page = StealthyFetcher.fetch(
                url,
                headless=True,
                disable_resources=True,
                network_idle=True,
                timeout=30000,
            )

            if page.status != 200:
                logger.warning(f"Internshala returned status {page.status} for {url}")
                continue

            # Internshala internship cards
            cards = (
                page.css('[class*="internship"]') or
                page.css('[class*="card"]') or
                page.css('[class*="listing"]')
            )

            seen_titles: set[str] = set()
            for card in cards:
                # Get title from heading
                title_el = (
                    card.css("h3::text") or card.css("h4::text") or
                    card.css("h5::text") or card.css("a::text")
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
                link_el = card.css("a[href*='/internship/']")
                link = ""
                if link_el:
                    href = link_el[0].attrib.get("href", "")
                    link = href if href.startswith("http") else f"https://internshala.com{href}"

                # Get company name
                company_el = card.css("[class*='company']::text") or card.css("a[class*='company']::text")
                company = clean_text(company_el[0]) if company_el else ""

                # Get stipend
                stipend = ""
                for el in card.css("*"):
                    text = clean_text(el.text)
                    if "₹" in text or "stipend" in text.lower():
                        stipend = _extract_stipend(text)
                        if stipend:
                            break

                # Get location
                location_el = card.css("[class*='location']::text")
                location = clean_text(location_el[0]) if location_el else ""

                # Get duration
                duration = ""
                for el in card.css("*"):
                    text = clean_text(el.text)
                    match = re.search(r'(\d+)\s*(month|week|day)', text.lower())
                    if match:
                        duration = match.group(0)
                        break

                if not link:
                    continue

                # Build eligibility and notes
                eligibility_parts = []
                if company:
                    eligibility_parts.append(f"Company: {company}")
                if location:
                    eligibility_parts.append(f"Location: {location}")
                if duration:
                    eligibility_parts.append(f"Duration: {duration}")
                if stipend:
                    eligibility_parts.append(f"Stipend: {stipend}")

                item = ScrapeItem(
                    title=title,
                    type="Internship",
                    source="Internshala",
                    link=link,
                    deadline="",
                    eligibility=". ".join(eligibility_parts) if eligibility_parts else "Check Internshala for details",
                    tags=["Internship"],
                    notes=f"Source: Internshala. {stipend} {duration}".strip()
                )
                items.append(item)
                logger.info(f"  Found: {title} at {company}")

        except Exception as e:
            logger.error(f"Error scraping Internshala {url}: {e}")

    logger.info(f"Internshala: scraped {len(items)} internships")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_internshala()
    for item in results:
        print(f"  {item.title} | {item.link} | {item.notes}")
