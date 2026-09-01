"""
CodeGladiators scraper.
CodeGladiators is TechGig's flagship coding competition — a SEASONAL annual
event. As of Sep 2026 there is NO live season:

  - The standalone domain www.codegladiators.com is a parked "for sale"
    GoDaddy domain (an HTTP fetch is redirected to a GoDaddy forsale lander,
    not to a real contest page).
  - TechGig's own page (https://www.techgig.com/codegladiators) returns 404,
    and TechGig's past-events page lists Code Gladiators only as a past event.
  - The most recent edition was Code Gladiators 2024 (open-coder round ended
    Jun 17, 2024); no 2025/2026 season has been announced.

The scraper therefore returns 0 items while the competition is not open. If
TechGig announces a new season at a live URL, update CODEGLADIATORS_URL / the
candidate-region logic below to scrape it.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

CODEGLADIATORS_URL = "https://www.techgig.com/codegladiators"
CODEGLADIATORS_BASE = "https://www.techgig.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_codegladiators() -> list[ScrapeItem]:
    """Scrape CodeGladiators events.

    CodeGladiators is a seasonal annual competition. As of Sep 2026 no season
    is open (the standalone domain is parked/for sale and TechGig's page is a
    404), so the correct result is 0 with a clear reason — not a fabricated
    entry with no real dates.
    """
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
        logger.info(
            "CodeGladiators is seasonal and no live season is currently open "
            "(standalone domain parked; techgig page not reachable). Returning 0."
        )
        return items

    if resp.status_code != 200:
        logger.warning(
            "CodeGladiators returned %d (no live season at %s) — nothing to "
            "scrape. The standalone codegladiators.com domain is a parked GoDaddy "
            "domain and TechGig's page 404s; the last edition ran in 2024.",
            resp.status_code,
            CODEGLADIATORS_URL,
        )
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=CODEGLADIATORS_URL)
    text = page.text or ""

    # Only build an entry if the page actually advertises a live/upcoming season.
    if not any(kw in text.lower() for kw in ["register", "open", "season", "round 1", "2026", "2027"]):
        logger.info(
            "CodeGladiators page contains no active season details; returning 0."
        )
        return items

    item = ScrapeItem(
        title="CodeGladiators",
        type="Competition",
        source="CodeGladiators",
        link=CODEGLADIATORS_URL,
        deadline="",
        eligibility="India (open to all)",
        tags=["competitive programming", "india", "techgig", "hackathon"],
        location="Online",
        notes="TechGig's flagship coding competition. Source: CodeGladiators.",
    )
    if not item.validate():
        items.append(item)

    logger.info("CodeGladiators: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_codegladiators()
    print(f"CodeGladiators: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
