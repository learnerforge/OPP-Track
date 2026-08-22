"""
lablab.ai scraper.
lablab.ai hosts AI/ML focused hackathons in partnership with tech companies.
The hackathons page at lablab.ai/hackathons lists active events.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

LABLAB_URL = "https://lablab.ai/hackathons"
LABLAB_BASE = "https://lablab.ai"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_lablab_ai() -> list[ScrapeItem]:
    """Scrape lablab.ai hackathons."""
    items: list[ScrapeItem] = []
    logger.info("Fetching lablab.ai hackathons: %s", LABLAB_URL)

    try:
        resp = httpx.get(
            LABLAB_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("lablab.ai request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("lablab.ai returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=LABLAB_URL)

    # lablab.ai hackathon cards
    cards = page.css(".hackathon-card, .card, [class*='hackathon'], article")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/hackathons/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{LABLAB_BASE}{href}"
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
        prize_el = card.css("[class*='prize'], [class*='reward']")
        prize_pool = clean_text(prize_el[0].text) if prize_el else ""

        tags = ["ai", "machine learning", "hackathon"]
        card_text = clean_text(card.text).lower()
        if "nlp" in card_text or "language" in card_text:
            tags.append("nlp")
        if "vision" in card_text or "image" in card_text:
            tags.append("computer vision")
        if "llm" in card_text or "gpt" in card_text:
            tags.append("llm")

        notes_parts = ["Source: lablab.ai."]
        if prize_pool:
            notes_parts.append(f"Prize: {prize_pool}.")

        item = ScrapeItem(
            title=title,
            type="Hackathon",
            source="lablab.ai",
            link=full_url,
            deadline=deadline,
            eligibility="Global participants",
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    # Fallback: parse hackathon links
    if not items:
        links = page.css("a[href*='/hackathons/']")
        for link_el in links:
            href = link_el.attrib.get("href", "")
            title = clean_text(link_el.text)
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else f"{LABLAB_BASE}{href}"
            if full_url in seen_links:
                continue
            seen_links.add(full_url)

            item = ScrapeItem(
                title=title,
                type="Hackathon",
                source="lablab.ai",
                link=full_url,
                deadline="",
                eligibility="Global participants",
                tags=["ai", "machine learning", "hackathon"],
                location="Online",
                notes="Source: lablab.ai.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("lablab.ai: scraped %d hackathons", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_lablab_ai()
    print(f"lablab.ai: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
