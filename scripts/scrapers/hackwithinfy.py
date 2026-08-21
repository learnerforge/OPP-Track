"""
HackWithInfy scraper.
Infosys coding competition. The site at infygram.com/hackwithinfy
displays event info.
"""

from __future__ import annotations

import logging
import re

import httpx
from scrapling import Selector

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

HWI_URL = "https://www.infygram.com/hackwithinfy"
HWI_BASE = "https://www.infygram.com"


def scrape_hackwithinfy() -> list[ScrapeItem]:
    """Scrape HackWithInfy contest info."""
    items: list[ScrapeItem] = []
    logger.info("Fetching HackWithInfy: %s", HWI_URL)

    try:
        resp = httpx.get(HWI_URL, timeout=30, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
    except Exception as e:
        logger.error("HackWithInfy request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("HackWithInfy returned %d", resp.status_code)
        return items

    page = Selector(resp.text, url=HWI_URL)
    text = page.text or ""

    # Look for year info
    year_match = re.search(r"20\d{2}", text)
    year = year_match.group(0) if year_match else "2026"

    # Create entry for HackWithInfy
    item = ScrapeItem(
        title=f"HackWithInfy {year}",
        type="Competition",
        source="HackWithInfy",
        link=HWI_URL,
        deadline="",
        eligibility="Pre-final and final year engineering students (India)",
        tags=["infosys", "india", "coding", "competitive programming"],
        location="Online",
        notes="Infosys coding competition. Pathway to Infosys scholarships and hiring. "
              "Source: HackWithInfy.",
    )
    if not item.validate():
        items.append(item)

    # Look for additional links/info on the page
    links = page.css("a")
    for link in links:
        href = link.attrib.get("href", "")
        link_text = (link.text or "").strip()
        if not href or not link_text or len(link_text) < 5:
            continue
        if any(kw in link_text.lower() for kw in ["register", "round", "rounds", "timeline"]):
            full_url = href if href.startswith("http") else f"{HWI_BASE}{href}"
            sub_item = ScrapeItem(
                title=f"HackWithInfy - {link_text}",
                type="Competition",
                source="HackWithInfy",
                link=full_url,
                deadline="",
                eligibility="Pre-final and final year engineering students (India)",
                tags=["infosys", "india", "coding"],
                location="Online",
                notes="Source: HackWithInfy.",
            )
            if not sub_item.validate():
                items.append(sub_item)

    logger.info("HackWithInfy: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackwithinfy()
    print(f"HackWithInfy: {len(results)} items")
    for item in results:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
