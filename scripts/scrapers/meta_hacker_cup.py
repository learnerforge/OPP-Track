"""
Meta Hacker Cup scraper.
Meta's annual open programming competition at
facebook.com/codingcompetitions/hacker-cup.
Static page with schedule info.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HACKER_CUP_URL = "https://www.facebook.com/codingcompetitions/hacker-cup"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_meta_hacker_cup() -> list[ScrapeItem]:
    """Scrape Meta Hacker Cup contest info."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Meta Hacker Cup: %s", HACKER_CUP_URL)

    try:
        resp = httpx.get(
            HACKER_CUP_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Meta Hacker Cup request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Meta Hacker Cup returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=HACKER_CUP_URL)
    text = page.text or ""

    # Extract current season year
    year_match = re.search(r"(?:Current Season|Season)[:\s]*(\d{4})", text)
    season_year = year_match.group(1) if year_match else "2025"

    # Create main entry for the Hacker Cup
    item = ScrapeItem(
        title=f"Meta Hacker Cup {season_year}",
        type="Competition",
        source="Meta Hacker Cup",
        link=HACKER_CUP_URL,
        deadline="",
        eligibility="Global participants",
        tags=["competitive programming", "algorithms", "meta", "facebook"],
        location="Online",
        notes="Meta's annual open programming competition. Prizes up to $20,000 for winner. "
              "Source: Meta Hacker Cup.",
    )
    if not item.validate():
        items.append(item)

    # Try to extract round details from the page
    # Look for round names and dates
    rounds = page.css("[class*='round'], [class*='Round'], tr, .schedule-item")
    for round_el in rounds:
        round_text = clean_text(round_el.text)
        if not round_text or len(round_text) < 10:
            continue

        # Look for round patterns
        round_match = re.search(
            r"(Practice Round|Round \d+|Finals? Round|Final Round)",
            round_text, re.IGNORECASE
        )
        if not round_match:
            continue

        round_name = f"Meta Hacker Cup {season_year} - {round_match.group(1)}"

        # Try to extract date
        date_match = re.search(
            r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+\d{1,2},?\s+\d{4})",
            round_text, re.IGNORECASE
        )
        deadline = parse_deadline(date_match.group(1)) if date_match else ""

        # Try to find a link
        link_el = round_el.css("a")
        href = ""
        if link_el:
            href = link_el[0].attrib.get("href", "")

        round_url = href if href and href.startswith("http") else HACKER_CUP_URL

        round_item = ScrapeItem(
            title=round_name,
            type="Competition",
            source="Meta Hacker Cup",
            link=round_url,
            deadline=deadline,
            eligibility="Global participants",
            tags=["competitive programming", "algorithms", "meta"],
            location="Online",
            notes=f"Source: Meta Hacker Cup. {round_name.split(' - ')[-1]}.",
        )
        if not round_item.validate():
            items.append(round_item)

    items = deduplicate_by_link(items)
    logger.info("Meta Hacker Cup: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_meta_hacker_cup()
    print(f"Meta Hacker Cup: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
