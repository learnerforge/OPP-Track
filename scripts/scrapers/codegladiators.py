"""
CodeGladiators scraper.
CodeGladiators is TechGig's flagship coding competition.
The main page at codegladiators.com has event info.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

CODEGLADIATORS_URL = "https://www.codegladiators.com/"
CODEGLADIATORS_BASE = "https://www.codegladiators.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_codegladiators() -> list[ScrapeItem]:
    """Scrape CodeGladiators events."""
    items: list[ScrapeItem] = []
    logger.info("Fetching CodeGladiators: %s", CODEGLADIATORS_URL)

    try:
        resp = httpx.get(
            CODEGLADIATORS_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("CodeGladiators request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("CodeGladiators returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=CODEGLADIATORS_URL)
    text = page.text or ""

    # Extract year
    year_match = re.search(r"(?:Code\s*Gladiators?\s*)(\d{4})", text, re.IGNORECASE)
    year = year_match.group(1) if year_match else str(__import__("datetime").datetime.now().year)

    # Create main entry
    main_url = CODEGLADIATORS_URL
    link_el = page.css("a[href*='register'], a[href*='sign'], a[href*='join']")
    if link_el:
        href = link_el[0].attrib.get("href", "")
        if href.startswith("http"):
            main_url = href

    item = ScrapeItem(
        title=f"CodeGladiators {year}",
        type="Competition",
        source="CodeGladiators",
        link=main_url,
        deadline="",
        eligibility="India (open to all)",
        tags=["competitive programming", "india", "techgig", "hackathon"],
        location="Online",
        notes="TechGig's flagship coding competition. Multiple rounds including "
              "speed coding and algorithmic challenges. Source: CodeGladiators.",
    )
    if not item.validate():
        items.append(item)

    # Look for additional event links
    links = page.css("a")
    for link_el in links:
        href = link_el.attrib.get("href", "")
        link_text = clean_text(link_el.text)
        if not link_text or len(link_text) < 5:
            continue
        if any(kw in link_text.lower() for kw in ["round", "qualifier", "final", "register", "timeline"]):
            full_url = href if href.startswith("http") else f"{CODEGLADIATORS_BASE}{href}"
            sub_item = ScrapeItem(
                title=f"CodeGladiators {year} - {link_text}",
                type="Competition",
                source="CodeGladiators",
                link=full_url,
                deadline="",
                eligibility="India (open to all)",
                tags=["competitive programming", "india", "techgig"],
                location="Online",
                notes="Source: CodeGladiators.",
            )
            if not sub_item.validate():
                items.append(sub_item)

    items = deduplicate_by_link(items)
    logger.info("CodeGladiators: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_codegladiators()
    print(f"CodeGladiators: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
