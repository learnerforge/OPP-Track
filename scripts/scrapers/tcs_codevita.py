"""
TCS CodeVita scraper.
Global coding contest by TCS. The site at codevita.tcsapps.com
displays current season info.
"""

from __future__ import annotations

import logging
import re

import httpx
from scrapling import Selector

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

CODEVITA_URL = "https://codevita.tcsapps.com/"
TCS_BASE = "https://codevita.tcsapps.com"


def scrape_tcs_codevita() -> list[ScrapeItem]:
    """Scrape TCS CodeVita contest info."""
    items: list[ScrapeItem] = []
    logger.info("Fetching TCS CodeVita: %s", CODEVITA_URL)

    try:
        resp = httpx.get(CODEVITA_URL, timeout=30, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
    except Exception as e:
        logger.error("TCS CodeVita request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("TCS CodeVita returned %d", resp.status_code)
        return items

    page = Selector(resp.text, url=CODEVITA_URL)
    text = page.text or ""

    # Look for season/round info
    season_match = re.search(r"(?:Season|CodeVita)\s*(\d+)", text, re.IGNORECASE)
    season_num = season_match.group(1) if season_match else "latest"

    # Look for any links to registration or contest pages
    links = page.css("a")
    contest_links = []
    for link in links:
        href = link.attrib.get("href", "")
        link_text = (link.text or "").strip()
        if href and link_text and len(link_text) > 3:
            full_url = href if href.startswith("http") else f"{TCS_BASE}{href}"
            contest_links.append({"title": link_text, "url": full_url})

    # Create entry for the main contest
    title = f"TCS CodeVita Season {season_num}" if season_num != "latest" else "TCS CodeVita"
    item = ScrapeItem(
        title=title,
        type="Competition",
        source="TCS CodeVita",
        link=CODEVITA_URL,
        deadline="",
        eligibility="Open to all (students and professionals)",
        tags=["coding", "tcs", "india", "global", "competitive programming"],
        location="Online",
        notes="TCS global coding contest with multiple rounds (Zone, Regional, Global). "
              "Hiring pipeline for TCS. Source: TCS CodeVita.",
    )
    if not item.validate():
        items.append(item)

    # Add sub-links as separate items if they look like contest rounds
    for cl in contest_links:
        round_title = cl["title"]
        if any(kw in round_title.lower() for kw in ["round", "register", "contest", "season", "qualifier"]):
            sub_item = ScrapeItem(
                title=f"TCS CodeVita - {round_title}",
                type="Competition",
                source="TCS CodeVita",
                link=cl["url"],
                deadline="",
                eligibility="Open to all",
                tags=["coding", "tcs", "india", "competitive programming"],
                location="Online",
                notes="Source: TCS CodeVita.",
            )
            if not sub_item.validate():
                items.append(sub_item)

    logger.info("TCS CodeVita: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_tcs_codevita()
    print(f"TCS CodeVita: {len(results)} items")
    for item in results:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
