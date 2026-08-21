"""
Devpost hackathon scraper — ENHANCED.
Tier-2 detail page scraping for eligibility, duration, tags from JSON-LD.
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

DEVPOST_URLS = [
    "https://devpost.com/hackathons?status[]=upcoming",
    "https://devpost.com/hackathons?status[]=open",
]

REQUEST_DELAY = 1.5


def _parse_date_range(text: str) -> str:
    """Parse Devpost date range like 'Aug 29 - Sep 01, 2026' into end date."""
    if not text:
        return ""
    match = re.search(r'-\s*(\w+\s+\d{1,2},?\s*\d{4})', text)
    if match:
        return parse_deadline(match.group(1))
    match = re.search(r'(\w+\s+\d{1,2},?\s*\d{4})', text)
    if match:
        return parse_deadline(match.group(1))
    return ""


def _compute_duration(start_iso: str, end_iso: str) -> str:
    """Compute human-readable duration from ISO datetime strings."""
    if not start_iso or not end_iso:
        return ""
    try:
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        delta = end - start
        hours = int(delta.total_seconds() / 3600)
        days = delta.days
        if hours <= 0:
            return ""
        if hours < 24:
            return f"{hours} Hours"
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


def _extract_detail_data(page) -> dict:
    """Extract rich data from a Devpost detail page: eligibility, duration, tags from JSON-LD."""
    updates = {}
    try:
        body_text = ""
        if page.body:
            body_text = re.sub(r'<[^>]+>', ' ', str(page.body))
            body_text = re.sub(r'\s+', ' ', body_text).strip()

        body_lower = body_text.lower()

        # JSON-LD extraction
        scripts = page.css('script[type="application/ld+json"]')
        for script in scripts:
            text = script.text or ""
            try:
                ld = json.loads(text)
                if ld.get("@type") == "Event":
                    # Duration from startDate/endDate
                    start = ld.get("startDate", "")
                    end = ld.get("endDate", "")
                    duration = _compute_duration(start, end)
                    if duration:
                        updates["duration"] = duration

                    # Deadline from endDate (submission deadline)
                    if end:
                        end_date_str = end.split("T")[0] if "T" in end else end
                        parsed_end = parse_deadline(end_date_str)
                        if parsed_end:
                            updates["deadline"] = parsed_end

                    # Organizer
                    org = ld.get("organizer", {})
                    if isinstance(org, dict):
                        org_name = org.get("name", "")
                        if org_name and org_name != "Devpost, Inc.":
                            updates["organizer"] = org_name

                    break
            except json.JSONDecodeError:
                continue

        # Eligibility from page text
        elig_parts = []
        if "student" in body_lower:
            elig_parts.append("Students")
        if "open to all" in body_lower or "everyone" in body_lower or "anyone" in body_lower:
            elig_parts.append("Open to all")
        if "developer" in body_lower and "student" not in body_lower:
            elig_parts.append("Developers")
        if "18" in body_lower and ("year" in body_lower or "age" in body_lower):
            elig_parts.append("18+")
        if "designer" in body_lower:
            elig_parts.append("Designers")
        if "beginner" in body_lower:
            elig_parts.append("Beginners welcome")
        if "college" in body_lower or "university" in body_lower:
            elig_parts.append("Students")

        # Look for "Who can participate" section
        elig_match = re.search(
            r'(?:eligibility|who\s+can\s+participate|requirements?)[:\s]*([^.]*(?:student|developer|open|anyone|everyone)[^.]*)',
            body_text[:3000], re.IGNORECASE
        )
        if elig_match:
            elig_text = elig_match.group(1).strip()[:200]
            if len(elig_text) > 10 and not any(p.lower() in elig_text.lower() for p in elig_parts):
                elig_parts.append(elig_text[:100])

        if elig_parts:
            updates["eligibility"] = ", ".join(list(set(elig_parts)))

        # Location from page text
        if not updates.get("location"):
            for loc in ("online", "hybrid", "in person", "offline"):
                if f"location:{loc}" in body_lower or f"location: {loc}" in body_lower:
                    updates["location"] = loc.title()
                    break

        # Team size
        team_match = re.search(r'(?:team|group)\s+(?:of\s+)?(?:up\s+to\s+)?(\d+)', body_lower)
        if team_match:
            updates["notes_extra"] = f"Team size: up to {team_match.group(1)}"

    except Exception as e:
        logger.debug(f"  Detail extraction error: {e}")
    return updates


def scrape_devpost() -> list[ScrapeItem]:
    """Scrape upcoming and open hackathons from Devpost with enhanced Tier-2 enrichment."""
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

            cards = page.css('.hackathon-tile')
            if not cards:
                logger.warning(f"No .hackathon-tile found for {url}")
                continue

            for card in cards:
                title_el = card.css('h3')
                title = clean_text(title_el[0].text if title_el else "")
                if not title or len(title) < 3:
                    continue

                link_el = card.css('a.tile-anchor[href]')
                href = link_el[0].attrib.get("href", "") if link_el else ""
                link = href if href.startswith("http") else f"https://devpost.com{href}" if href else ""

                if not link:
                    continue

                date_el = card.css('.submission-period')
                date_text = clean_text(date_el[0].text if date_el else "")
                deadline = _parse_date_range(date_text)

                tag_els = card.css('.theme-label')
                tags = [clean_text(t.attrib.get('title', '')) for t in tag_els if clean_text(t.attrib.get('title', ''))]

                location = ""
                for info_icon in card.css('.info-with-icon'):
                    spans = info_icon.css('span')
                    for sp in spans:
                        sp_text = clean_text(sp.text)
                        if sp_text.lower() in ('online', 'offline', 'hybrid', 'in person'):
                            location = sp_text
                            break
                    if location:
                        break

                host_el = card.css('.host-label') or card.css('.host')
                host = clean_text(host_el[0].attrib.get('title', '') if host_el else "")

                prize_el = card.css('.prize-amount')
                if prize_el:
                    prize_html = str(prize_el[0])
                    prize_text = re.sub(r'<[^>]+>', '', prize_html)
                    prize = clean_text(prize_text)
                else:
                    prize = ""

                participants_el = card.css('.participants strong')
                participants = clean_text(participants_el[0].text if participants_el else "")

                status_el = card.css('.hackathon-status')
                status = clean_text(status_el[0].text if status_el else "")

                notes_parts = ["Source: Devpost."]
                if location:
                    notes_parts.append(f"Location: {location}.")
                if host:
                    notes_parts.append(f"Host: {host}.")
                if prize:
                    notes_parts.append(f"Prize: {prize}.")
                if participants:
                    notes_parts.append(f"Participants: {participants}.")
                if status:
                    notes_parts.append(f"Status: {status}.")

                eligibility = "Open to all developers"

                item = ScrapeItem(
                    title=title,
                    type="Hackathon",
                    source="Devpost",
                    link=link,
                    deadline=deadline,
                    eligibility=eligibility,
                    tags=tags,
                    notes=" ".join(notes_parts),
                    location=location,
                    organizer=host,
                    prize_pool=prize,
                    participants=participants,
                )
                items.append(item)
                logger.info(f"  Found: {title} | {deadline} | {link}")

        except Exception as e:
            logger.error(f"Error scraping Devpost {url}: {e}")

    logger.info(f"Devpost: scraped {len(items)} hackathons")

    # Tier-2: Visit ALL detail pages for eligibility + duration
    logger.info(f"Running Tier-2 detail enrichment for all {len(items)} Devpost items...")
    for i, item in enumerate(items):
        if i > 0:
            time.sleep(REQUEST_DELAY)
        logger.info(f"  [{i+1}/{len(items)}] Enriching: {item.title}")
        try:
            page = StealthyFetcher.fetch(
                item.link,
                headless=True,
                disable_resources=True,
                network_idle=True,
                timeout=20000,
            )
            if page.status == 200:
                detail = _extract_detail_data(page)
                if detail.get("eligibility") and detail["eligibility"] != "Open to all developers":
                    item.eligibility = detail["eligibility"]
                if detail.get("duration") and not item.duration:
                    item.duration = detail["duration"]
                if detail.get("deadline") and not item.deadline:
                    item.deadline = detail["deadline"]
                if detail.get("organizer") and not item.organizer:
                    item.organizer = detail["organizer"]
                if detail.get("location") and not item.location:
                    item.location = detail["location"]
                if detail.get("notes_extra"):
                    item.notes = f"{item.notes} {detail['notes_extra']}".strip()
                logger.info(f"    -> elig={item.eligibility[:50]} duration={item.duration}")
        except Exception as e:
            logger.debug(f"    Enrichment error: {e}")

    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_devpost()
    for item in results:
        print(f"  {item.title} | {item.deadline} | duration={item.duration} | {item.eligibility[:60]} | {item.link}")
