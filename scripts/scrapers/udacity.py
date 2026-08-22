"""
Udacity scraper.
Udacity offers Nanodegree programs and various scholarship programs
in partnership with tech companies (AWS, Bertelsmann, Google, etc.).
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

UDACITY_SCHOLARSHIPS_URL = "https://www.udacity.com/scholarships"
UDACITY_BASE = "https://www.udacity.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_udacity() -> list[ScrapeItem]:
    """Scrape Udacity scholarship programs."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Udacity scholarships: %s", UDACITY_SCHOLARSHIPS_URL)

    try:
        resp = httpx.get(
            UDACITY_SCHOLARSHIPS_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Udacity request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Udacity returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=UDACITY_SCHOLARSHIPS_URL)

    # Udacity scholarship cards
    cards = page.css(".scholarship-card, .card, [class*='scholarship'], article, [class*='program']")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/scholarships/']")
        if not link_el:
            link_el = card.css("a[href*='/program']")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{UDACITY_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Try to find deadline
        deadline_el = card.css("[class*='deadline'], [class*='date'], time, [class*='end']")
        deadline = ""
        if deadline_el:
            deadline_text = clean_text(deadline_el[0].text)
            deadline = parse_deadline(deadline_text)

        # Try to extract deadline from card text
        if not deadline:
            card_text = clean_text(card.text)
            date_match = re.search(
                r"(?:deadline|apply by|due|closes?)[:\s]*"
                r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
                r"\s+\d{1,2},?\s+\d{4})",
                card_text, re.IGNORECASE
            )
            if date_match:
                deadline = parse_deadline(date_match.group(1))

        tags = ["scholarship", "online learning", "nanodegree"]
        card_text = clean_text(card.text).lower()
        if "aws" in card_text:
            tags.append("aws")
        if "google" in card_text:
            tags.append("google")
        if "ai" in card_text or "artificial intelligence" in card_text:
            tags.append("ai")
        if "cybersecurity" in card_text or "security" in card_text:
            tags.append("cybersecurity")
        if "data science" in card_text:
            tags.append("data science")

        notes_parts = ["Source: Udacity."]
        if "fully funded" in card_text or "free" in card_text:
            notes_parts.append("Fully funded scholarship.")

        item = ScrapeItem(
            title=title,
            type="Certification",
            source="Udacity",
            link=full_url,
            deadline=deadline,
            eligibility="Global participants (18+)",
            tags=tags,
            location="Online",
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    # Fallback: parse scholarship links
    if not items:
        links = page.css("a[href*='/scholarships/']")
        for link_el in links:
            href = link_el.attrib.get("href", "")
            title = clean_text(link_el.text)
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else f"{UDACITY_BASE}{href}"
            if full_url in seen_links:
                continue
            seen_links.add(full_url)

            item = ScrapeItem(
                title=title,
                type="Certification",
                source="Udacity",
                link=full_url,
                deadline="",
                eligibility="Global participants (18+)",
                tags=["scholarship", "online learning", "nanodegree"],
                location="Online",
                notes="Source: Udacity.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Udacity: scraped %d scholarships", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_udacity()
    print(f"Udacity: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
