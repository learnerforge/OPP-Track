"""
Qureka scraper.
Qureka (https://www.qureka.com) is India's mobile-first trivia quiz app.
Its public website is a static landing page for downloading the app --
it does not expose contest/quiz listings (with titles, links, and
deadlines) that could be represented as opportunities.

As of Sep 2026 the homepage contains only promotional copy and app-store
links, and /contests, /events, /competitions etc. all return 404. This
scraper therefore parses the homepage for any real quiz-related entries
and returns an empty list when, as is currently the case, none exist.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

QUREKA_URL = "https://www.qureka.com/"
QUREKA_BASE = "https://www.qureka.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_qureka() -> list[ScrapeItem]:
    """Scrape Qureka for quiz contests.

    The public website has no contest listings. Returns an empty list when
    no real quiz entries are found (the current state of the platform).
    """
    items: list[ScrapeItem] = []
    logger.info("Fetching Qureka: %s", QUREKA_URL)

    try:
        resp = httpx.get(
            QUREKA_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Qureka request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Qureka returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=QUREKA_URL)

    # Qureka only exposes an app download landing page. There are no
    # contest listings with registration deadlines. If the site later adds
    # real quiz/contest cards, they can be parsed here.
    candidate_cards = page.css("article, [class*='contest'], [class*='quiz'], [class*='event'], .card")
    real_cards = []

    seen_links = set()
    for card in candidate_cards:
        link_el = card.css("a[href*='/contests'], a[href*='/events'], a[href*='/quiz'], a[href*='/competitions']")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        if not href or href in ("#", "#/"):
            continue

        title_el = card.css("h1, h2, h3, h4, [class*='title']")
        title = clean_text(title_el[0].get_all_text()) if title_el else ""
        if title.startswith("×"):
            continue
        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{QUREKA_BASE}/{href.lstrip('/')}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        deadline_el = card.css("time, [class*='date'], [class*='deadline']")
        deadline_text = clean_text(deadline_el[0].get_all_text()) if deadline_el else ""

        item = ScrapeItem(
            title=title,
            type="Hackathon",
            source="Qureka",
            link=full_url,
            deadline="",  # computed by caller from deadline_text rendering if present
            eligibility="India; play via the Qureka mobile app",
            tags=["quiz", "india"],
            location="Online",
            notes="Source: Qureka. " + (f"Deadline text: {deadline_text}." if deadline_text else "Quiz contest page."),
        )
        if not item.validate():
            real_cards.append(item)

    if real_cards:
        items = deduplicate_by_link(real_cards)
    else:
        logger.info("Qureka: no contest listings found on the public site (expected)")
    logger.info("Qureka: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_qureka()
    print(f"Qureka: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")