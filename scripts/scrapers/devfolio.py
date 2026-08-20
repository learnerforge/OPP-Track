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
    """Extract the hackathon-specific JSON from a Devfolio detail page."""
    try:
        body = str(page.body) if page.body else ""

        # Try __NEXT_DATA__ first (most reliable)
        scripts = page.css('script#__NEXT_DATA__')
        if scripts:
            script_text = scripts[0].text or ""
            data = json.loads(script_text)
            page_props = data.get("props", {}).get("pageProps", {})
            if page_props:
                return page_props

        # Try dehydratedState — find the FIRST hackathon query (the current one)
        match = re.search(r'"dehydratedState":\s*\{[^}]*"queries":\s*\[(\{.*?\})\]', body, re.DOTALL)
        if match:
            try:
                queries_str = "[" + match.group(1) + "]"
                queries = json.loads(queries_str)
                for query in queries:
                    state = query.get("state", {})
                    data = state.get("data", {})
                    hackathon = data.get("hackathon", {})
                    if hackathon and hackathon.get("name"):
                        return hackathon
            except json.JSONDecodeError:
                pass

        # Fallback: look for the hackathon JSON blob with name + themes
        match = re.search(r'"hackathon":\s*(\{[^}]*"name":"[^"]+"[^}]*"themes":\[[^\]]+\][^}]*\})', body)
        if match:
            try:
                return json.loads(match.group(1))
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
            # Check if this is a hackathon dict directly or wrapped in queries
            hackathon = json_data
            if "hackathon" in json_data and isinstance(json_data["hackathon"], dict):
                hackathon = json_data["hackathon"]
            elif "queries" in json_data:
                # Extract from queries
                for query in json_data.get("queries", []):
                    state = query.get("state", {})
                    data = state.get("data", {})
                    h = data.get("hackathon", {})
                    if h and h.get("name"):
                        hackathon = h
                        break

            # Themes/tags
            themes = hackathon.get("themes", [])
            if themes:
                tag_names = [t.get("theme", {}).get("name", "") for t in themes if t.get("theme", {}).get("name")]
                if tag_names and tag_names != ["No Restrictions"]:
                    updates["tags"] = tag_names

            # Prize pool
            prize_details = hackathon.get("prizeDetails", [])
            if prize_details:
                total = 0
                currency = ""
                for track in prize_details:
                    for prize in track.get("prizes", []):
                        amt = prize.get("amount", 0)
                        if amt:
                            total += amt
                            currency = prize.get("currency", "USD")
                if total > 0:
                    symbol = "$" if currency == "USD" else "₹" if currency == "INR" else currency + " "
                    updates["prize_pool"] = f"{symbol}{total:,}"

            # Organizer
            organizer = hackathon.get("organizer", {})
            if organizer and isinstance(organizer, dict):
                org_name = organizer.get("name", "")
                if org_name:
                    updates["organizer"] = org_name

            # Participants
            participants = hackathon.get("participants_count")
            if participants:
                updates["participants"] = str(participants)

            # Team size
            team_min = hackathon.get("team_min")
            team_max = hackathon.get("team_max")
            if team_min and team_max:
                updates["notes_extra"] = f"Team size: {team_min}-{team_max}"

            # Online/offline
            online = hackathon.get("online")
            if online is True:
                updates["location"] = "Online"
            elif online is False:
                city = hackathon.get("city", "")
                country = hackathon.get("country", "")
                if city or country:
                    updates["location"] = f"{city}, {country}" if city else country

            # Dates
            starts_at = hackathon.get("starts_at", "")
            ends_at = hackathon.get("ends_at", "")
            if starts_at:
                date_match = re.match(r'(\d{4}-\d{2}-\d{2})', starts_at)
                if date_match:
                    updates["deadline"] = date_match.group(1)

        # Fallback: HTML-based extraction for missing fields
        if not updates.get("deadline"):
            deadline_match = re.search(r'(\d{4}-\d{2}-\d{2})', body)
            if deadline_match:
                updates["deadline"] = deadline_match.group(1)

        if not updates.get("tags"):
            # Look for theme/tag labels in HTML
            tag_matches = re.findall(r'"name":"([^"]+)".*?"theme":\{"name":"([^"]+)"\}', body)
            if tag_matches:
                tags = list(set(t[1] for t in tag_matches if t[1] != "No Restrictions"))
                if tags:
                    updates["tags"] = tags[:5]

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
