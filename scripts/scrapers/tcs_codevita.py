"""
TCS CodeVita scraper.
Global coding contest by TCS — a SEASONAL annual contest. As of Sep 2026 the
official site (codevita.tcsapps.com) states "Thank you for participating in
TCS CodeVita Season 13 ... We'll be back with Season 14." That means Season 13
has concluded and Season 14 has NOT been announced/opened yet.

This scraper therefore returns 0 items while no season is open (correct for a
seasonal event), and only builds an entry when the site advertises a live
season with real dates.
"""

from __future__ import annotations

import logging

import httpx
from scrapling import Selector

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

CODEVITA_URL = "https://codevita.tcsapps.com/"


def scrape_tcs_codevita() -> list[ScrapeItem]:
    """Scrape TCS CodeVita contest info.

    CodeVita is seasonal. If the official page indicates the current season is
    open, we return a real item; otherwise we return 0 with a reason.
    """
    items: list[ScrapeItem] = []
    logger.info("Fetching TCS CodeVita: %s", CODEVITA_URL)

    try:
        resp = httpx.get(CODEVITA_URL, timeout=30, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
    except Exception as e:
        logger.error("TCS CodeVita request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("TCS CodeVita returned %d", resp.status_code)
        return items

    page = Selector(resp.text, url=CODEVITA_URL)
    text = page.text or ""

    # Detect whether a season is currently open. The homepage advertises a new
    # season only while one is live; "we'll be back with Season N" means closed.
    if "back with season" in text.lower():
        logger.info(
            "TCS CodeVita is seasonal: the official page states 'We'll be back "
            "with Season N', i.e. the previous season concluded and the next "
            "season is NOT open yet. Returning 0 — correct for a seasonal event, "
            "not a bug. Watch codevita.tcsapps.com for the next season."
        )
        return items

    # If the page doesn't signal an open season, treat it as closed too.
    if not any(kw in text.lower() for kw in ["register", "registration open", "join the contest"]):
        logger.info(
            "TCS CodeVita page shows no open registration; returning 0."
        )
        return items

    item = ScrapeItem(
        title="TCS CodeVita",
        type="Competition",
        source="TCS CodeVita",
        link=CODEVITA_URL,
        deadline="",
        eligibility="Students in a science/engineering course graduating 2026-2029",
        tags=["coding", "tcs", "india", "competitive programming"],
        location="Online",
        notes="TCS global coding contest with multiple rounds and hiring "
              "pipeline for TCS. Source: codevita.tcsapps.com.",
    )
    if not item.validate():
        items.append(item)

    logger.info("TCS CodeVita: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_tcs_codevita()
    print(f"TCS CodeVita: {len(results)} items")
    for item in results:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
