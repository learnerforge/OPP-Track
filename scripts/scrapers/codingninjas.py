"""
CodingNinjas scraper.
CodingNinjas is an India-focused coding education platform.
The contests page lists upcoming coding challenges and hiring tests.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

CODINGNINJAS_URL = "https://www.codingninjas.com/contests"
CODINGNINJAS_BASE = "https://www.codingninjas.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_codingninjas() -> list[ScrapeItem]:
    """Scrape CodingNinjas contests."""
    items: list[ScrapeItem] = []
    logger.info("Fetching CodingNinjas: %s", CODINGNINJAS_URL)

    try:
        resp = httpx.get(
            CODINGNINJAS_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("CodingNinjas request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("CodingNinjas returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=CODINGNINJAS_URL)

    cards = page.css(".contest-card, .card, [class*='contest'], article")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/contests/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 3:
            continue

        full_url = href if href.startswith("http") else f"{CODINGNINJAS_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        deadline_el = card.css(".deadline, [class*='date'], [class*='time']")
        deadline_raw = clean_text(deadline_el[0].text) if deadline_el else ""
        deadline = parse_deadline(deadline_raw)

        item = ScrapeItem(
            title=f"[CodingNinjas] {title}",
            type="Hackathon",
            source="CodingNinjas",
            link=full_url,
            deadline=deadline,
            eligibility="India-focused; students and professionals",
            tags=["coding", "contest", "codingninjas", "india"],
            location="Online",
            notes="India-focused coding education platform with contests. Source: codingninjas.com.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("CodingNinjas: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_codingninjas()
    print(f"CodingNinjas: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
