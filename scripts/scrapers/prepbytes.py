"""
PrepBytes scraper.
PrepBytes is an India-focused coding practice and contest platform.
The contests page lists upcoming coding challenges and hiring challenges.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

PREPBYTES_URL = "https://www.prepbytes.com/contests"
PREPBYTES_BASE = "https://www.prepbytes.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_prepbytes() -> list[ScrapeItem]:
    """Scrape PrepBytes contests."""
    items: list[ScrapeItem] = []
    logger.info("Fetching PrepBytes: %s", PREPBYTES_URL)

    try:
        resp = httpx.get(
            PREPBYTES_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("PrepBytes request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("PrepBytes returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=PREPBYTES_URL)

    cards = page.css(".contest-card, .card, [class*='contest'], article, div[class*='problem']")
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

        full_url = href if href.startswith("http") else f"{PREPBYTES_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        deadline_el = card.css(".deadline, [class*='date'], [class*='time']")
        deadline_raw = clean_text(deadline_el[0].text) if deadline_el else ""
        deadline = parse_deadline(deadline_raw)

        item = ScrapeItem(
            title=f"[PrepBytes] {title}",
            type="Hackathon",
            source="PrepBytes",
            link=full_url,
            deadline=deadline,
            eligibility="India-focused; open to all students and professionals",
            tags=["coding", "contest", "prepbytes", "india", "hiring"],
            location="Online",
            notes="India-focused coding contests and hiring challenges. Source: prepbytes.com.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("PrepBytes: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_prepbytes()
    print(f"PrepBytes: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
