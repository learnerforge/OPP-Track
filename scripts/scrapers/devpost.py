"""
Devpost hackathon scraper.
Devpost is a Rails app with server-rendered HTML — uses StealthyFetcher for reliability.
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


def _parse_date_range(text: str) -> str:
    """Parse Devpost date range like 'Aug 29 - Sep 01, 2026' into end date."""
    if not text:
        return ""
    # "Aug 29 - Sep 01, 2026" → take the end date
    match = re.search(r'-\s*(\w+\s+\d{1,2},?\s*\d{4})', text)
    if match:
        return parse_deadline(match.group(1))
    # "Aug 29, 2026"
    match = re.search(r'(\w+\s+\d{1,2},?\s*\d{4})', text)
    if match:
        return parse_deadline(match.group(1))
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

            # Devpost cards: div.hackathon-tile
            cards = page.css('.hackathon-tile')
            if not cards:
                logger.warning(f"No .hackathon-tile found for {url}")
                continue

            for card in cards:
                # Title: h3 inside the card
                title_el = card.css('h3')
                title = clean_text(title_el[0].text if title_el else "")
                if not title or len(title) < 3:
                    continue

                # Link: a.tile-anchor[href]
                link_el = card.css('a.tile-anchor[href]')
                href = link_el[0].attrib.get("href", "") if link_el else ""
                link = href if href.startswith("http") else f"https://devpost.com{href}" if href else ""

                if not link:
                    continue

                # Date range: div.submission-period
                date_el = card.css('.submission-period')
                date_text = clean_text(date_el[0].text if date_el else "")
                deadline = _parse_date_range(date_text)

                # Tags: span.theme-label
                tag_els = card.css('.theme-label')
                tags = [clean_text(t.attrib.get('title', '')) for t in tag_els if clean_text(t.attrib.get('title', ''))]

                # Location: look for Online/Offline/Hybrid in info-with-icon spans
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

                # Host: div.host / .host-label
                host_el = card.css('.host-label') or card.css('.host')
                host = clean_text(host_el[0].attrib.get('title', '') if host_el else "")

                # Prize: div.prize-amount — use str() to get full nested text
                prize_el = card.css('.prize-amount')
                if prize_el:
                    prize_html = str(prize_el[0])
                    prize_text = re.sub(r'<[^>]+>', '', prize_html)
                    prize = clean_text(prize_text)
                else:
                    prize = ""

                # Participants: div.participants strong
                participants_el = card.css('.participants strong')
                participants = clean_text(participants_el[0].text if participants_el else "")

                # Status: div.hackathon-status
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

                item = ScrapeItem(
                    title=title,
                    type="Hackathon",
                    source="Devpost",
                    link=link,
                    deadline=deadline,
                    eligibility="Open to all developers",
                    tags=tags,
                    notes=" ".join(notes_parts),
                )
                items.append(item)
                logger.info(f"  Found: {title} | {deadline} | {link}")

        except Exception as e:
            logger.error(f"Error scraping Devpost {url}: {e}")

    logger.info(f"Devpost: scraped {len(items)} hackathons")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_devpost()
    for item in results:
        print(f"  {item.title} | {item.deadline} | {item.link}")
