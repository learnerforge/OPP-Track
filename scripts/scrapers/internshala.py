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
    """Fetch an Internshala detail page and extract data from JSON-LD schema."""
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

        # Extract JSON-LD JobPosting schema (most reliable data source)
        scripts = page.css('script')
        for script in scripts:
            text = script.text or ""
            if '"@type":"JobPosting"' in text or '"@type": "JobPosting"' in text:
                try:
                    import json
                    data = json.loads(text)
                except json.JSONDecodeError:
                    match = re.search(r'(\{.*"@type"\s*:\s*"JobPosting".*\})', text, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                        except json.JSONDecodeError:
                            continue
                    else:
                        continue

                # Deadline from validThrough
                valid_through = data.get("validThrough", "")
                if valid_through:
                    parsed = parse_deadline(valid_through.split(" ")[0])
                    if parsed:
                        updates["deadline"] = parsed

                # Company from hiringOrganization
                org = data.get("hiringOrganization", {})
                if org and isinstance(org, dict):
                    org_name = org.get("name", "")
                    if org_name:
                        updates["organizer"] = org_name

                # Location from jobLocation
                locations = data.get("jobLocation", [])
                if locations and isinstance(locations, list):
                    for loc in locations:
                        addr = loc.get("address", {})
                        city = addr.get("addressLocality", "")
                        region = addr.get("addressRegion", "")
                        if city:
                            updates["location"] = f"{city}, {region}" if region else city
                            break

                # Duration and eligibility from description
                desc = data.get("description", "")
                desc_text = re.sub(r'<[^>]+>', ' ', desc)
                desc_text = re.sub(r'\s+', ' ', desc_text).strip()

                # Duration
                dur_match = re.search(r'duration\s+of\s+(\d+)\s*(month|week|day)s?', desc_text.lower())
                if dur_match:
                    updates["duration"] = dur_match.group(0).title()

                # Eligibility from "Who can apply" section
                elig_match = re.search(r'who\s+can\s+apply[:\s]*(.*?)(?=\s*stipend|\s*other|\s*$)', desc_text.lower())
                if elig_match:
                    elig_text = elig_match.group(1).strip()[:300]
                    if len(elig_text) > 10:
                        # Clean up eligibility text
                        elig_text = re.sub(r'only those candidates can apply who:?\s*', '', elig_text)
                        elig_text = re.sub(r'\d+\.\s*', '', elig_text)
                        updates["eligibility"] = elig_text.strip()[:200]

                # Skills from description
                skills_match = re.search(r'skills?\s+required[:\s]*(.*?)(?=\s*other|\s*$)', desc_text.lower())
                if skills_match:
                    skills = skills_match.group(1).strip()[:200]
                    if skills:
                        updates["notes_extra"] = f"Skills: {skills}"

                # Stipend from baseSalary
                salary = data.get("baseSalary", {})
                if salary and isinstance(salary, dict):
                    value = salary.get("value", {})
                    if value and isinstance(value, dict):
                        min_val = value.get("minValue", 0)
                        max_val = value.get("maxValue", 0)
                        currency = salary.get("currency", "INR")
                        if min_val and max_val:
                            symbol = "₹" if currency == "INR" else "$" if currency == "USD" else currency + " "
                            updates["stipend"] = f"{symbol}{min_val:,} - {max_val:,} /month"
                        elif min_val:
                            symbol = "₹" if currency == "INR" else "$" if currency == "USD" else currency + " "
                            updates["stipend"] = f"{symbol}{min_val:,} /month"

                break

        # Fallback: meta tags if JSON-LD not found
        if not updates.get("deadline"):
            meta_desc = page.css('meta[name="description"]')
            if meta_desc:
                content = meta_desc[0].attrib.get("content", "")
                deadline_match = re.search(r'(\w+\s+\d{1,2},?\s*\d{4})', content)
                if deadline_match:
                    parsed = parse_deadline(deadline_match.group(1))
                    if parsed:
                        updates["deadline"] = parsed

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

            # Tier-2: Visit detail pages for missing data (max 10 to avoid timeout)
            detail_limit = min(10, len(card_data))
            for i, card in enumerate(card_data):
                if i >= detail_limit:
                    # Skip detail page, use listing data only
                    eligibility_parts = []
                    if card["company"]:
                        eligibility_parts.append(f"Company: {card['company']}")
                    if card["location"]:
                        eligibility_parts.append(f"Location: {card['location']}")
                    if card["duration"]:
                        eligibility_parts.append(f"Duration: {card['duration']}")
                    if card["stipend"]:
                        eligibility_parts.append(f"Stipend: {card['stipend']}")

                    item = ScrapeItem(
                        title=card["title"],
                        type="Internship",
                        source="Internshala",
                        link=card["link"],
                        deadline="",
                        eligibility=". ".join(eligibility_parts) if eligibility_parts else "Check Internshala for details",
                        tags=["Internship"],
                        notes=f"Source: Internshala. {card['stipend']} {card['duration']}".strip(),
                        organizer=card["company"],
                        duration=card["duration"],
                    )
                    items.append(item)
                    continue
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
