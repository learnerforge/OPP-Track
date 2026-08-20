"""
Internshala internship scraper — ENHANCED.
Fixes:
  1. Tier-2 detail page scraping for deadline, company, duration
  2. Better URL construction from listing page
  3. More robust card selectors
"""

from __future__ import annotations

import re
import logging
import time
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

INTERNSHALA_URLS = [
    "https://internshala.com/internships",
    "https://internshala.com/internships/work-from-home-internships",
]

REQUEST_DELAY = 1.5


def _extract_stipend(text: str) -> str:
    """Extract stipend from text like '₹ 10,000 /month'."""
    if not text:
        return ""
    match = re.search(r'₹\s*[\d,]+(?:\s*/\s*month)?', text)
    return match.group(0) if match else ""


def _extract_duration_from_text(text: str) -> str:
    """Extract duration like '3 Months' from free text."""
    match = re.search(r'(\d+)\s*(month|week|day)s?', text.lower())
    if match:
        return match.group(0).title()
    return ""


def _scrape_detail_page(link: str) -> dict:
    """Fetch an Internshala detail page and extract deadline, company, duration, eligibility."""
    updates = {}
    try:
        page = StealthyFetcher.fetch(
            link,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=25000,
        )
        if page.status != 200:
            return updates

        body_text = ""
        if page.body:
            body_text = re.sub(r'<[^>]+>', ' ', str(page.body))
            body_text = re.sub(r'\s+', ' ', body_text).strip()

        # Deadline: look for "Deadline" or "Last date to apply"
        deadline_match = re.search(
            r'(?:deadline|last\s+date\s+to\s+apply|apply\s+by)[:\s]*(\w+\s+\d{1,2},?\s*\d{4})',
            body_text, re.IGNORECASE
        )
        if deadline_match:
            parsed = parse_deadline(deadline_match.group(1))
            if parsed:
                updates["deadline"] = parsed

        # Duration
        dur_match = re.search(r'(\d+)\s*(month|week|day)s?', body_text.lower())
        if dur_match:
            updates["duration"] = dur_match.group(0).title()

        # Eligibility: look for "Who can apply" or "Eligibility" section
        elig_match = re.search(
            r'(?:who\s+can\s+apply|eligibility|requirements?)[:\s]*([^.]*(?:student|graduate|fresher|bachelor|master|degree)[^.]*)',
            body_text, re.IGNORECASE
        )
        if elig_match:
            elig_text = elig_match.group(1).strip()[:200]
            if len(elig_text) > 10:
                updates["eligibility"] = elig_text

        # Company from page title or heading
        company_match = re.search(r'at\s+([\w\s&]+?)(?:\s*[-–|]|$)', body_text[:500])
        if company_match:
            company = company_match.group(1).strip()
            if len(company) > 2 and len(company) < 60:
                updates["organizer"] = company

        # Location from page
        loc_match = re.search(r'(?:location|city)[:\s]*(\w[\w\s,]+?)(?:\s*[-–|.]|$)', body_text[:1000], re.IGNORECASE)
        if loc_match:
            updates["location"] = loc_match.group(1).strip()[:50]

    except Exception as e:
        logger.debug(f"  Detail page error for {link}: {e}")

    return updates


def scrape_internshala() -> list[ScrapeItem]:
    """Scrape internships from Internshala with Tier-2 detail enrichment."""
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

            # Strategy 1: Look for internship listing cards with links
            # Internshala uses <a href="/internship/detail/..."> for each listing
            detail_links = page.css('a[href*="/internship/detail/"]')
            seen_links: set[str] = set()
            card_data = []

            for link_el in detail_links:
                href = link_el.attrib.get("href", "")
                if not href or href in seen_links:
                    continue
                full_link = href if href.startswith("http") else f"https://internshala.com{href}"
                seen_links.add(href)

                # Get title from the link text or nearby heading
                title = clean_text(link_el.text)
                if not title or len(title) < 3:
                    # Try parent card
                    parent = getattr(link_el, "parent", None)
                    if parent:
                        h3 = parent.css("h3")
                        if h3:
                            title = clean_text(h3[0].text)
                if not title or len(title) < 3:
                    continue

                # Get company from nearby elements
                card = getattr(link_el, "parent", None)
                company = ""
                stipend = ""
                location = ""
                duration = ""

                if card:
                    # Company: look for company name element
                    company_el = card.css("[class*='company']") or card.css("a[class*='company']")
                    if company_el:
                        company = clean_text(company_el[0].text)

                    # Stipend
                    for el in card.css("*"):
                        text = clean_text(el.text)
                        if "₹" in text:
                            stipend = _extract_stipend(text)
                            if stipend:
                                break

                    # Location
                    loc_el = card.css("[class*='location']")
                    if loc_el:
                        location = clean_text(loc_el[0].text)

                    # Duration
                    for el in card.css("*"):
                        text = clean_text(el.text)
                        dur = _extract_duration_from_text(text)
                        if dur:
                            duration = dur
                            break

                card_data.append({
                    "title": title,
                    "link": full_link,
                    "company": company,
                    "stipend": stipend,
                    "location": location,
                    "duration": duration,
                })

            logger.info(f"  Found {len(card_data)} internship cards")

            # Tier-2: Visit detail pages for missing data
            for i, card in enumerate(card_data):
                detail_updates = {}
                if i > 0:
                    time.sleep(REQUEST_DELAY)
                detail_updates = _scrape_detail_page(card["link"])

                # Build eligibility
                eligibility_parts = []
                if card["company"]:
                    eligibility_parts.append(f"Company: {card['company']}")
                if detail_updates.get("organizer") and not card["company"]:
                    eligibility_parts.append(f"Company: {detail_updates['organizer']}")
                if card["location"]:
                    eligibility_parts.append(f"Location: {card['location']}")
                elif detail_updates.get("location"):
                    eligibility_parts.append(f"Location: {detail_updates['location']}")
                if card["duration"]:
                    eligibility_parts.append(f"Duration: {card['duration']}")
                elif detail_updates.get("duration"):
                    eligibility_parts.append(f"Duration: {detail_updates['duration']}")
                if card["stipend"]:
                    eligibility_parts.append(f"Stipend: {card['stipend']}")
                if detail_updates.get("eligibility"):
                    eligibility_parts.append(detail_updates["eligibility"])

                # Notes
                notes_parts = ["Source: Internshala."]
                if card["stipend"]:
                    notes_parts.append(card["stipend"])
                if card["duration"]:
                    notes_parts.append(card["duration"])

                item = ScrapeItem(
                    title=card["title"],
                    type="Internship",
                    source="Internshala",
                    link=card["link"],
                    deadline=detail_updates.get("deadline", ""),
                    eligibility=". ".join(eligibility_parts) if eligibility_parts else "Check Internshala for details",
                    tags=["Internship"],
                    notes=" ".join(notes_parts),
                    location=detail_updates.get("location", ""),
                    organizer=detail_updates.get("organizer", card["company"]),
                    duration=detail_updates.get("duration", card["duration"]),
                )
                items.append(item)
                logger.info(f"  [{i+1}/{len(card_data)}] {card['title']} | deadline={item.deadline or '(none)'} | org={item.organizer}")

        except Exception as e:
            logger.error(f"Error scraping Internshala {url}: {e}")

    logger.info(f"Internshala: scraped {len(items)} internships")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_internshala()
    for item in results:
        print(f"  {item.title} | {item.deadline or '(no deadline)'} | {item.organizer} | {item.link}")
