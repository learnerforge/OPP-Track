"""
InterviewBit scraper.
InterviewBit (now Scaler) hosts coding contests and interview prep.
The contests page lists upcoming coding challenges.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

INTERVIEWBIT_URL = "https://www.interviewbit.com/contests/"
INTERVIEWBIT_BASE = "https://www.interviewbit.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_interviewbit() -> list[ScrapeItem]:
    """Scrape InterviewBit contests."""
    items: list[ScrapeItem] = []
    logger.info("Fetching InterviewBit: %s", INTERVIEWBIT_URL)

    try:
        resp = httpx.get(
            INTERVIEWBIT_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("InterviewBit request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("InterviewBit returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=INTERVIEWBIT_URL)

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

        full_url = href if href.startswith("http") else f"{INTERVIEWBIT_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        deadline_el = card.css(".deadline, [class*='date'], [class*='time']")
        deadline_raw = clean_text(deadline_el[0].text) if deadline_el else ""
        deadline = parse_deadline(deadline_raw)

        prize_el = card.css("[class*='prize'], [class*='reward']")
        prize_pool = clean_text(prize_el[0].text) if prize_el else ""

        item = ScrapeItem(
            title=f"[InterviewBit] {title}",
            type="Hackathon",
            source="InterviewBit",
            link=full_url,
            deadline=deadline,
            eligibility="Global students and professionals",
            tags=["coding", "contest", "interviewbit", "scaler"],
            location="Online",
            prize_pool=prize_pool,
            notes="Coding contests and interview prep platform. Source: interviewbit.com.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("InterviewBit: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_interviewbit()
    print(f"InterviewBit: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
