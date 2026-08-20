"""
Devfolio hackathon scraper — ENHANCED.
Extracts JSON payload from detail pages for rich data:
  themes (tags), organizer, prize, participants, dates, online/offline.
"""

from __future__ import annotations

import re
import json
import logging
import time
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

DEVFOLIO_BASE = "https://devfolio.co"
DEVFOLIO_OPEN = f"{DEVFOLIO_BASE}/hackathons/open"
DEVFOLIO_UPCOMING = f"{DEVFOLIO_BASE}/hackathons/upcoming"

SKIP_TITLES = {
    "applications open", "open", "upcoming", "past",
    "all open hackathons", "all upcoming hackathons",
}

REQUEST_DELAY = 1.5


def _parse_devfolio_date(text: str) -> str:
    """Parse 'Starts 27/08/26' into YYYY-MM-DD."""
    match = re.search(r'starts?\s+(\d{1,2})/(\d{1,2})/(\d{2,4})', text.lower())
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return ""


def _extract_json_from_devfolio(page) -> dict | None:
    """Extract the hackathon-specific JSON from a Devfolio detail page.

    Returns a dict with hackathon data from __NEXT_DATA__ including:
      name, starts_at, ends_at, team_min, team_max, themes, online, city, country,
      aggregatePrizeValue, aggregatePrizeCurrency, participants_count, organizer
    """
    try:
        body = str(page.body) if page.body else ""

        # Try __NEXT_DATA__ first (most reliable)
        scripts = page.css('script#__NEXT_DATA__')
        if scripts:
            script_text = scripts[0].text or ""
            script_text = script_text.replace('\\/', '/')
            try:
                data = json.loads(script_text)
                page_props = data.get("props", {}).get("pageProps", {})
                if not page_props:
                    return None

                result = {}

                # 1. Main hackathon object (has name, dates, team sizes)
                hackathon = page_props.get("hackathon", {})
                if hackathon and hackathon.get("name"):
                    result.update(hackathon)

                # 2. Themes from dehydratedState (React Query cache)
                #    This is the only reliable source for the CURRENT hackathon's themes
                dehydrated = page_props.get("dehydratedState", {})
                queries = dehydrated.get("queries", [])
                for query in queries:
                    state_data = query.get("state", {}).get("data")
                    if isinstance(state_data, list):
                        for entry in state_data:
                            if isinstance(entry, dict) and "hackathons" in entry:
                                hackathons_list = entry["hackathons"]
                                if isinstance(hackathons_list, list) and hackathons_list:
                                    themes_raw = hackathons_list[0].get("themes", [])
                                    if themes_raw:
                                        names = [
                                            t["theme"]["name"]
                                            for t in themes_raw
                                            if isinstance(t, dict)
                                            and isinstance(t.get("theme"), dict)
                                            and t["theme"].get("name")
                                            and t["theme"]["name"] != "No Restrictions"
                                        ]
                                        if names:
                                            result["themes"] = names[:5]
                                        # Also grab fields not in pageProps.hackathon
                                        if not result.get("online") and "online" in hackathons_list[0]:
                                            result["online"] = hackathons_list[0]["online"]
                                        if not result.get("organizer") and "organizer" in hackathons_list[0]:
                                            org = hackathons_list[0]["organizer"]
                                            if isinstance(org, dict):
                                                result["organizer"] = org.get("name", "")
                                            elif isinstance(org, str):
                                                result["organizer"] = org
                                        if not result.get("city") and "city" in hackathons_list[0]:
                                            result["city"] = hackathons_list[0]["city"]
                                        if not result.get("country") and "country" in hackathons_list[0]:
                                            result["country"] = hackathons_list[0]["country"]

                if result.get("name"):
                    return result

            except json.JSONDecodeError:
                pass

    except Exception as e:
        logger.debug(f"  JSON extraction error: {e}")
    return None


def _scrape_detail_page(link: str) -> dict:
    """Fetch a Devfolio detail page and extract rich data from JSON/HTML."""
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

        body = str(page.body) if page.body else ""
        body_text = re.sub(r'<[^>]+>', ' ', body)
        body_text = re.sub(r'\s+', ' ', body_text).strip()

        # Extract JSON payload
        json_data = _extract_json_from_devfolio(page)

        if json_data:
            # Themes
            if json_data.get("themes"):
                updates["tags"] = json_data["themes"]

            # Organizer
            if json_data.get("organizer"):
                updates["organizer"] = json_data["organizer"]

            # Online/offline
            if "online" in json_data:
                if json_data["online"]:
                    updates["location"] = "Online"
                else:
                    city = json_data.get("city", "")
                    country = json_data.get("country", "")
                    if city or country:
                        updates["location"] = f"{city}, {country}" if city else country

            # Dates from starts_at
            starts_at = json_data.get("starts_at", "")
            if starts_at:
                date_match = re.match(r'(\d{4}-\d{2}-\d{2})', starts_at)
                if date_match:
                    updates["deadline"] = date_match.group(1)

            # Participants from body
            part_match = re.search(r'"participants_count"\s*:\s*(\d+)', body)
            if part_match:
                updates["participants"] = part_match.group(1)

            # Prize from aggregatePrizeValue
            prize_match = re.search(r'"aggregatePrizeValue"\s*:\s*(\d+)', body)
            currency_match = re.search(r'"aggregatePrizeCurrency"\s*:\s*"([^"]+)"', body)
            if prize_match:
                amount = int(prize_match.group(1))
                if amount > 0:
                    currency = currency_match.group(1) if currency_match else "USD"
                    symbol = "$" if currency == "USD" else "₹" if currency == "INR" else currency + " "
                    updates["prize_pool"] = f"{symbol}{amount:,}"

        # Fallback: HTML-based extraction for missing fields
        if not updates.get("deadline"):
            deadline_match = re.search(r'(\d{4}-\d{2}-\d{2})', body)
            if deadline_match:
                updates["deadline"] = deadline_match.group(1)

        # Eligibility from page text
        elig_parts = []
        if "student" in body_text.lower():
            elig_parts.append("Students")
        if "open to all" in body_text.lower() or "everyone" in body_text.lower():
            elig_parts.append("Open to all")
        if "developer" in body_text.lower():
            elig_parts.append("Developers")
        if elig_parts:
            updates["eligibility"] = ", ".join(elig_parts)

    except Exception as e:
        logger.debug(f"  Detail page error for {link}: {e}")

    return updates


def _scrape_page(url: str) -> list[ScrapeItem]:
    """Scrape a single Devfolio listing page."""
    items: list[ScrapeItem] = []
    logger.info(f"Fetching Devfolio: {url}")

    page = StealthyFetcher.fetch(
        url,
        headless=True,
        disable_resources=True,
        network_idle=True,
        timeout=30000,
    )

    if page.status != 200:
        logger.warning(f"Devfolio returned status {page.status} for {url}")
        return items

    # --- Extract card titles + links ---
    cards = page.css('a[class*="Link__LinkBase"]')
    card_data = []
    for card in cards:
        href = card.attrib.get("href", "")
        if ".devfolio.co" not in href:
            continue
        title_el = card.css("h3::text")
        if not title_el:
            continue
        title = clean_text(title_el[0])
        if not title or title.lower() in SKIP_TITLES:
            continue
        card_data.append({"title": title, "link": href})

    # --- Extract start dates in page order ---
    date_els = page.find_by_regex(re.compile(r'Starts \d{1,2}/\d{1,2}/\d{2,4}'), first_match=False)
    dates = [_parse_devfolio_date(str(el.text)) for el in date_els]

    # --- Extract participation counts in page order ---
    part_els = page.find_by_regex(re.compile(r'\+\d+\s*participat', re.IGNORECASE), first_match=False)
    participations = [clean_text(el.text) for el in part_els]

    # --- Match by position ---
    for i, card in enumerate(card_data):
        deadline = dates[i] if i < len(dates) else ""
        participation = participations[i] if i < len(participations) else ""

        notes_parts = ["Source: Devfolio."]
        if participation:
            notes_parts.append(participation)

        item = ScrapeItem(
            title=card["title"],
            type="Hackathon",
            source="Devfolio",
            link=card["link"],
            deadline=deadline,
            eligibility="Open to all students and developers",
            tags=[],
            notes=" ".join(notes_parts),
        )
        items.append(item)
        logger.info(f"  Found: {card['title']} | {deadline}")

    return items


def scrape_devfolio() -> list[ScrapeItem]:
    """Scrape open and upcoming hackathons from Devfolio with Tier-2 enrichment."""
    items: list[ScrapeItem] = []
    for url in [DEVFOLIO_OPEN, DEVFOLIO_UPCOMING]:
        try:
            items.extend(_scrape_page(url))
        except Exception as e:
            logger.error(f"Error scraping Devfolio {url}: {e}")

    # Tier-2: Visit detail pages for items missing tags (max 10)
    need_enrichment = [item for item in items if not item.tags or not item.organizer]
    enrich_limit = min(10, len(need_enrichment))
    logger.info(f"Devfolio: scraped {len(items)} hackathons from listings")
    logger.info(f"Running Tier-2 detail enrichment for {enrich_limit} Devfolio items missing tags...")

    for i, item in enumerate(need_enrichment[:enrich_limit]):
        if item.tags and item.organizer:
            continue  # Already has good data

        if i > 0:
            time.sleep(REQUEST_DELAY)

        logger.info(f"  [{i+1}/{len(items)}] Enriching: {item.title}")
        updates = _scrape_detail_page(item.link)

        if updates.get("tags"):
            item.tags = updates["tags"]
        if updates.get("prize_pool"):
            item.prize_pool = updates["prize_pool"]
        if updates.get("organizer"):
            item.organizer = updates["organizer"]
        if updates.get("participants"):
            item.participants = updates["participants"]
        if updates.get("deadline") and not item.deadline:
            item.deadline = updates["deadline"]
        if updates.get("location"):
            item.location = updates["location"]
        if updates.get("eligibility"):
            item.eligibility = updates["eligibility"]
        if updates.get("notes_extra"):
            item.notes = f"{item.notes} {updates['notes_extra']}".strip()

        logger.info(f"    -> tags={item.tags} organizer={item.organizer} prize={item.prize_pool}")

    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_devfolio()
    for item in results:
        print(f"  {item.title} | {item.deadline} | tags={item.tags} | {item.link}")
