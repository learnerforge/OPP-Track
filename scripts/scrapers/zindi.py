"""
Zindi scraper.
Zindi is Africa's leading data science competition platform.
The competitions page at zindi.africa/competitions lists active challenges.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

ZINDI_URL = "https://zindi.africa/competitions"
ZINDI_BASE = "https://zindi.africa"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_zindi() -> list[ScrapeItem]:
    """Scrape Zindi competitions."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Zindi competitions: %s", ZINDI_URL)

    try:
        resp = httpx.get(
            ZINDI_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Zindi request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Zindi returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=ZINDI_URL)

    # Zindi competition cards
    cards = page.css(".competition-card, .card, [class*='competition'], article")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/competitions/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title'], .card-title")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{ZINDI_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Try to find deadline
        deadline_el = card.css("[class*='deadline'], [class*='date'], time, [class*='end']")
        deadline = ""
        if deadline_el:
            deadline_text = clean_text(deadline_el[0].text)
            deadline = parse_deadline(deadline_text)

        # Try to find prize info
        prize_el = card.css("[class*='prize'], [class*='reward'], [class*='amount']")
        prize_pool = clean_text(prize_el[0].text) if prize_el else ""

        # Tags
        tag_els = card.css("[class*='tag'], [class*='category'], .badge")
        tags = ["machine learning", "data science", "africa"]
        for tag_el in tag_els[:5]:
            tag_text = clean_text(tag_el.text)
            if tag_text and len(tag_text) < 30:
                tags.append(tag_text.lower())

        notes_parts = ["Source: Zindi Africa."]
        if prize_pool:
            notes_parts.append(f"Prize: {prize_pool}.")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="Zindi",
            link=full_url,
            deadline=deadline,
            eligibility="Global participants (Africa-focused)",
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    # Fallback: parse competition links from page text if no cards found
    if not items:
        links = page.css("a[href*='/competitions/']")
        for link_el in links:
            href = link_el.attrib.get("href", "")
            title = clean_text(link_el.text)
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else f"{ZINDI_BASE}{href}"
            if full_url in seen_links:
                continue
            seen_links.add(full_url)

            item = ScrapeItem(
                title=title,
                type="Competition",
                source="Zindi",
                link=full_url,
                deadline="",
                eligibility="Global participants (Africa-focused)",
                tags=["machine learning", "data science", "africa"],
                location="Online",
                notes="Source: Zindi Africa.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Zindi: scraped %d competitions", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_zindi()
    print(f"Zindi: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
