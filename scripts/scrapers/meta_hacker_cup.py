"""
Meta Hacker Cup scraper.
Meta's annual open programming competition at
facebook.com/codingcompetitions/hacker-cup.
JS-rendered page (fb.com) — fetched with StealthyFetcher.
Emits an item per round whose start date is still in the future;
a fully concluded season honestly produces zero items.
"""

from __future__ import annotations

import logging
import re
from datetime import date

from scrapling.fetchers import StealthyFetcher
from scrapling.parser import Selector

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HACKER_CUP_URL = "https://www.facebook.com/codingcompetitions/hacker-cup"
HACKER_CUP_BASE = "https://www.facebook.com"

ROUND_LINK_RE = re.compile(r"/codingcompetitions/hacker-cup/20\d\d/[\w-]*round")
ROUND_NAME_RE = re.compile(r"(Practice Round|Round \d+|Final Round)", re.IGNORECASE)
ROUND_DATE_RE = re.compile(r"(\d{1,2}\s+\w+\s+\d{4})", re.IGNORECASE)
SEASON_RE = re.compile(r"Current Season[:\s]*(\d{4})")


def scrape_meta_hacker_cup() -> list[ScrapeItem]:
    """Scrape Meta Hacker Cup rounds with future start dates."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Meta Hacker Cup: %s", HACKER_CUP_URL)

    try:
        page = StealthyFetcher.fetch(
            HACKER_CUP_URL,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=60000,
        )
    except Exception as e:
        logger.error("Meta Hacker Cup StealthyFetcher failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("Meta Hacker Cup returned %d", page.status)
        return items

    body = page.body
    html = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
    sel = Selector(html)

    text = clean_text(sel.get_all_text())
    season_match = SEASON_RE.search(text)
    season_year = season_match.group(1) if season_match else ""
    if season_year:
        logger.info("Meta Hacker Cup: current season is %s", season_year)

    today = date.today().isoformat()

    round_links = sel.css('a[href*="codingcompetitions/hacker-cup/"][href*="round"]')
    logger.info("Meta Hacker Cup: found %d round cards", len(round_links))

    seen = set()
    for link_el in round_links:
        href = link_el.attrib.get("href", "")
        if not ROUND_LINK_RE.search(href):
            continue

        full_url = href if href.startswith("http") else f"{HACKER_CUP_BASE}{href}"
        if full_url in seen:
            continue

        heading = link_el.css('[role="heading"][aria-level="2"]')
        round_name = clean_text(heading[0].get_all_text()) if heading else clean_text(link_el.get_all_text())
        if not ROUND_NAME_RE.search(round_name):
            continue

        status = ""
        status_el = link_el.css("span")
        for s in status_el:
            st = clean_text(s.get_all_text())
            if st in ("Concluded", "Opened", "Upcoming", "Registration Open", "Registration opens"):
                status = st
                break

        card_text = clean_text(link_el.get_all_text())
        date_match = ROUND_DATE_RE.search(card_text)
        deadline = parse_deadline(date_match.group(1)) if date_match else ""

        # Only rounds that haven't started yet are actionable
        if not deadline or deadline < today:
            continue

        if status and status != "Concluded":
            notes = f"Source: Meta Hacker Cup. Status: {status}."
        else:
            notes = "Source: Meta Hacker Cup."

        item = ScrapeItem(
            title=f"Meta Hacker Cup {round_name}",
            type="Competition",
            source="Meta Hacker Cup",
            link=full_url,
            deadline=deadline,
            eligibility="Global participants",
            tags=["competitive programming", "algorithms", "meta", "facebook"],
            location="Online",
            notes=notes,
        )
        if not item.validate():
            items.append(item)
            logger.info("  Found: %s | %s | %s", item.title, deadline, full_url[:70])

    if not items:
        season_txt = f"season {season_year}" if season_year else "current season"
        logger.info("Meta Hacker Cup: no upcoming rounds listed (%s) — returning 0 items", season_txt)

    items = deduplicate_by_link(items)
    logger.info("Meta Hacker Cup: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_meta_hacker_cup()
    print(f"Meta Hacker Cup: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")