"""
Devfolio hackathon scraper — ENHANCED.
Extracts JSON payload from detail pages for rich data:
  themes (tags), organizer, prize, participants, dates, online/offline, duration.
"""

from __future__ import annotations

import re
import json
import logging
import time
from datetime import datetime
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


def _compute_duration(starts_at: str, ends_at: str) -> str:
    """Compute human-readable duration from ISO timestamps."""
    if not starts_at or not ends_at:
        return ""
    try:
        start = datetime.fromisoformat(starts_at)
        end = datetime.fromisoformat(ends_at)
        delta = end - start
        days = delta.days
        if days <= 0:
            return ""
        if days == 1:
            return "1 Day"
        if days < 7:
            return f"{days} Days"
        weeks = days // 7
        remaining = days % 7
        if remaining:
            return f"{weeks} Weeks {remaining} Days"
        return f"{weeks} Weeks"
    except (ValueError, TypeError):
        return ""


def _format_prize(value: int, currency: str) -> str:
    """Format prize value with currency symbol."""
    if value <= 0:
        return ""
    symbols = {"USD": "$", "INR": "\u20b9", "EUR": "\u20ac", "GBP": "\u00a3"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{value:,}"


def _extract_json_from_devfolio(page) -> dict | None:
    """Extract the hackathon-specific JSON from a Devfolio detail page."""
    try:
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

                # aggregatePrizeValue/Currency are at pageProps level, NOT inside hackathon
                result["_aggregatePrizeValue"] = page_props.get("aggregatePrizeValue", 0)
                result["_aggregatePrizeCurrency"] = page_props.get("aggregatePrizeCurrency", "USD")

                hackathon = page_props.get("hackathon", {})
                if hackathon and hackathon.get("name"):
                    result.update(hackathon)

                # Settings for organizer fallback and registration deadline
                settings = hackathon.get("settings", {})
                if settings:
                    result["settings"] = settings
                    # Registration deadline (more accurate than starts_at)
                    reg_end = settings.get("reg_ends_at", "")
                    if reg_end:
                        result["_reg_ends_at"] = reg_end

                # Themes from dehydratedState
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

        json_data = _extract_json_from_devfolio(page)

        if json_data:
            # Themes
            if json_data.get("themes"):
                updates["tags"] = json_data["themes"]

            # Organizer from dehydratedState or settings fallback
            if json_data.get("organizer"):
                updates["organizer"] = json_data["organizer"]
            else:
                settings = json_data.get("settings", {})
                if settings:
                    email = settings.get("contact_email", "")
                    if email:
                        domain = email.split("@")[-1] if "@" in email else ""
                        if domain and domain not in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com"):
                            updates["organizer"] = domain.split(".")[0].title()
                    site = settings.get("site", "")
                    if not updates.get("organizer") and site:
                        site_match = re.search(r'://(?:www\.)?([^/]+)', site)
                        if site_match:
                            updates["organizer"] = site_match.group(1).split(".")[0].title()

            # Online/offline
            if "online" in json_data:
                if json_data["online"]:
                    updates["location"] = "Online"
                else:
                    city = json_data.get("city", "")
                    country = json_data.get("country", "")
                    if city or country:
                        updates["location"] = f"{city}, {country}" if city else country

            # Duration from starts_at/ends_at
            starts_at = json_data.get("starts_at", "")
            ends_at = json_data.get("ends_at", "")
            duration = _compute_duration(starts_at, ends_at)
            if duration:
                updates["duration"] = duration

            # Deadline from reg_ends_at (registration close) is more accurate than starts_at
            reg_ends = json_data.get("_reg_ends_at", "")
            if reg_ends:
                date_match = re.match(r'(\d{4}-\d{2}-\d{2})', reg_ends)
                if date_match:
                    updates["deadline"] = date_match.group(1)
            if not updates.get("deadline"):
                starts_at = json_data.get("starts_at", "")
                if starts_at:
                    date_match = re.match(r'(\d{4}-\d{2}-\d{2})', starts_at)
                    if date_match:
                        updates["deadline"] = date_match.group(1)

            # Participants from body
            part_match = re.search(r'"participants_count"\s*:\s*(\d+)', body)
            if part_match:
                updates["participants"] = part_match.group(1)

            # Prize from aggregatePrizeValue (at pageProps level, not hackathon)
            prize_value = json_data.get("_aggregatePrizeValue", 0)
            prize_currency = json_data.get("_aggregatePrizeCurrency", "USD")
            if prize_value:
                updates["prize_pool"] = _format_prize(int(prize_value), prize_currency)

            # Team size in notes
            team_min = json_data.get("team_min", 0)
            team_max = json_data.get("team_max", 0)
            if team_min and team_max:
                updates["notes_extra"] = f"Team size: {team_min}-{team_max}"
            elif team_min:
                updates["notes_extra"] = f"Team size: {team_min}+"

        # Eligibility from page text
        body_text = re.sub(r'<[^>]+>', ' ', body) if body else ""
        body_text = re.sub(r'\s+', ' ', body_text).strip()
        elig_parts = []
        body_lower = body_text.lower()
        if "student" in body_lower:
            elig_parts.append("Students")
        if "open to all" in body_lower or "everyone" in body_lower or "anyone" in body_lower:
            elig_parts.append("Open to all")
        if "developer" in body_lower and "student" not in body_lower:
            elig_parts.append("Developers")
        if "beginner" in body_lower:
            elig_parts.append("Beginners welcome")
        if elig_parts:
            updates["eligibility"] = ", ".join(elig_parts)

        # Tags fallback from description keywords when themes are empty
        if not updates.get("tags"):
            tag_keywords = [
                "blockchain", "ai", "machine learning", "web3", "nft", "defi",
                "cloud", "fintech", "health", "education", "sustainability",
                "iot", "cybersecurity", "data science", "ar", "vr",
                "open innovation", "beginner", "hardware", "software",
            ]
            desc = json_data.get("desc", "") if json_data else ""
            desc_lower = desc.lower() if desc else ""
            found_tags = [kw.title() for kw in tag_keywords if kw in body_lower or kw in desc_lower]
            if found_tags:
                updates["tags"] = found_tags[:5]

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

    date_els = page.find_by_regex(re.compile(r'Starts \d{1,2}/\d{1,2}/\d{2,4}'), first_match=False)
    dates = [_parse_devfolio_date(str(el.text)) for el in date_els]

    part_els = page.find_by_regex(re.compile(r'\+\d+\s*participat', re.IGNORECASE), first_match=False)
    participations = [clean_text(el.text) for el in part_els]

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

    need_enrichment = [item for item in items if not item.tags or not item.organizer or not item.prize_pool or not item.duration]
    logger.info(f"Devfolio: scraped {len(items)} hackathons from listings")
    logger.info(f"Running Tier-2 detail enrichment for {len(need_enrichment)} Devfolio items...")

    for i, item in enumerate(need_enrichment):
        if i > 0:
            time.sleep(REQUEST_DELAY)

        logger.info(f"  [{i+1}/{len(need_enrichment)}] Enriching: {item.title}")
        updates = _scrape_detail_page(item.link)

        if updates.get("tags") and not item.tags:
            item.tags = updates["tags"]
        if updates.get("prize_pool") and not item.prize_pool:
            item.prize_pool = updates["prize_pool"]
        if updates.get("organizer") and not item.organizer:
            item.organizer = updates["organizer"]
        if updates.get("participants") and not item.participants:
            item.participants = updates["participants"]
        if updates.get("deadline") and not item.deadline:
            item.deadline = updates["deadline"]
        if updates.get("location") and not item.location:
            item.location = updates["location"]
        if updates.get("duration") and not item.duration:
            item.duration = updates["duration"]
        if updates.get("eligibility"):
            item.eligibility = updates["eligibility"]
        if updates.get("notes_extra"):
            item.notes = f"{item.notes} {updates['notes_extra']}".strip()

        logger.info(f"    -> tags={item.tags} prize={item.prize_pool} duration={item.duration} org={item.organizer}")

    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_devfolio()
    for item in results:
        print(f"  {item.title} | {item.deadline} | tags={item.tags} | prize={item.prize_pool} | duration={item.duration} | {item.link}")
