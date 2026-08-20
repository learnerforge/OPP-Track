"""
Internshala internship scraper — ENHANCED.
Tier-2 detail page scraping for deadline, company, duration via JSON-LD.
"""

from __future__ import annotations

import re
import json
import logging
import time
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

INTERNSHALA_URLS = [
    "https://internshala.com/internships",
    "https://internshala.com/internships/work-from-home-internships",
]

REQUEST_DELAY = 1.0
DETAIL_LIMIT = 50


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


def _extract_company_from_url(url: str) -> str:
    """Extract company name from Internshala URL slug.
    e.g., /internship/detail/marketing-internship-at-sportskeeda123456 -> sportskeeda
    """
    match = re.search(r'-at-([a-z0-9]+?)(\d{10,})$', url.lower())
    if match:
        name = match.group(1).replace("-", " ").title()
        return name
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

        # Extract JSON-LD JobPosting schema
        scripts = page.css('script')
        for script in scripts:
            text = script.text or ""
            if '"@type":"JobPosting"' in text or '"@type": "JobPosting"' in text:
                try:
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
                            symbol = "\u20b9" if currency == "INR" else "$" if currency == "USD" else currency + " "
                            updates["stipend"] = f"{symbol}{min_val:,} - {max_val:,} /month"
                        elif min_val:
                            symbol = "\u20b9" if currency == "INR" else "$" if currency == "USD" else currency + " "
                            updates["stipend"] = f"{symbol}{min_val:,} /month"

                # Employment type and industry (bonus fields)
                emp_type = data.get("employmentType", "")
                if emp_type:
                    updates["employment_type"] = emp_type

                industry = data.get("industry", "")
                if industry:
                    updates["industry"] = industry

                total_openings = data.get("totalJobOpenings", 0)
                if total_openings:
                    updates["total_openings"] = str(total_openings)

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

            detail_links = page.css('a[href*="/internship/detail/"]')
            seen_links: set[str] = set()
            card_data = []

            for link_el in detail_links:
                href = link_el.attrib.get("href", "")
                if not href or href in seen_links:
                    continue
                full_link = href if href.startswith("http") else f"https://internshala.com{href}"
                seen_links.add(href)

                title = clean_text(link_el.text)
                if not title or len(title) < 3:
                    parent = getattr(link_el, "parent", None)
                    if parent:
                        h3 = parent.css("h3")
                        if h3:
                            title = clean_text(h3[0].text)
                if not title or len(title) < 3:
                    continue

                card = getattr(link_el, "parent", None)
                company = ""
                stipend = ""
                location = ""
                duration = ""

                if card:
                    company_el = card.css("[class*='company']") or card.css("a[class*='company']")
                    if company_el:
                        company = clean_text(company_el[0].text)

                    for el in card.css("*"):
                        text = clean_text(el.text)
                        if "\u20b9" in text:
                            stipend = _extract_stipend(text)
                            if stipend:
                                break

                    loc_el = card.css("[class*='location']")
                    if loc_el:
                        location = clean_text(loc_el[0].text)

                    for el in card.css("*"):
                        text = clean_text(el.text)
                        dur = _extract_duration_from_text(text)
                        if dur:
                            duration = dur
                            break

                # Fallback company from URL
                if not company:
                    company = _extract_company_from_url(full_link)

                card_data.append({
                    "title": title,
                    "link": full_link,
                    "company": company,
                    "stipend": stipend,
                    "location": location,
                    "duration": duration,
                })

            logger.info(f"  Found {len(card_data)} internship cards")

            detail_limit = min(DETAIL_LIMIT, len(card_data))
            for i, card in enumerate(card_data):
                if i >= detail_limit:
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

                notes_parts = ["Source: Internshala."]
                if card["stipend"]:
                    notes_parts.append(card["stipend"])
                elif detail_updates.get("stipend"):
                    notes_parts.append(detail_updates["stipend"])
                if card["duration"]:
                    notes_parts.append(card["duration"])
                elif detail_updates.get("duration"):
                    notes_parts.append(detail_updates["duration"])
                if detail_updates.get("industry"):
                    notes_parts.append(f"Industry: {detail_updates['industry']}.")
                if detail_updates.get("total_openings"):
                    notes_parts.append(f"Openings: {detail_updates['total_openings']}.")

                final_organizer = detail_updates.get("organizer", "") or card["company"]
                final_location = detail_updates.get("location", "") or card["location"]
                final_duration = detail_updates.get("duration", "") or card["duration"]

                item = ScrapeItem(
                    title=card["title"],
                    type="Internship",
                    source="Internshala",
                    link=card["link"],
                    deadline=detail_updates.get("deadline", ""),
                    eligibility=". ".join(eligibility_parts) if eligibility_parts else "Check Internshala for details",
                    tags=["Internship"],
                    notes=" ".join(notes_parts),
                    location=final_location,
                    organizer=final_organizer,
                    duration=final_duration,
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
        print(f"  {item.title} | {item.deadline or '(no deadline)'} | {item.organizer} | {item.duration} | {item.link}")
