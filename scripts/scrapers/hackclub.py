"""
Hack Club scraper.
Hack Club is a nonprofit network of high school coding clubs and hackathons.
The hackathons page at hackclub.com/hackathons lists upcoming events.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HACKCLUB_URL = "https://hackclub.com/hackathons"
HACKCLUB_BASE = "https://hackclub.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_hackclub() -> list[ScrapeItem]:
    """Scrape Hack Club hackathons."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Hack Club hackathons: %s", HACKCLUB_URL)

    try:
        resp = httpx.get(
            HACKCLUB_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Hack Club request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Hack Club returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=HACKCLUB_URL)

    # Hack Club hackathon cards/links
    cards = page.css(".hackathon-card, .card, [class*='hackathon'], article, .event")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='hackathon'], a[href*='event']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{HACKCLUB_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Try to find deadline
        deadline_el = card.css("[class*='deadline'], [class*='date'], time")
        deadline = ""
        if deadline_el:
            deadline_text = clean_text(deadline_el[0].text)
            deadline = parse_deadline(deadline_text)

        tags = ["hackathon", "high school", "hack club"]

        item = ScrapeItem(
            title=title,
            type="Hackathon",
            source="Hack Club",
            link=full_url,
            deadline=deadline,
            eligibility="High school students",
            tags=tags,
            location="Hybrid",
            notes="Source: Hack Club.",
        )
        if not item.validate():
            items.append(item)

    # Fallback: look for any hackathon-related links
    if not items:
        all_links = page.css("a")
        for link_el in all_links:
            href = link_el.attrib.get("href", "")
            title = clean_text(link_el.text)
            if not title or len(title) < 5:
                continue
            if not any(kw in title.lower() for kw in ["hackathon", "event", "jam"]):
                continue
            full_url = href if href.startswith("http") else f"{HACKCLUB_BASE}{href}"
            if full_url in seen_links:
                continue
            seen_links.add(full_url)

            item = ScrapeItem(
                title=title,
                type="Hackathon",
                source="Hack Club",
                link=full_url,
                deadline="",
                eligibility="High school students",
                tags=["hackathon", "high school", "hack club"],
                location="Hybrid",
                notes="Source: Hack Club.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Hack Club: scraped %d hackathons", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackclub()
    print(f"Hack Club: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
