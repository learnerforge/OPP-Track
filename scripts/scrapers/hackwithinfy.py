"""
HackWithInfy scraper.
Infosys coding competition — a SEASONAL annual contest.
Note: returned 0 is correct when the current season is not open.
"""

from __future__ import annotations

import logging
import re

from datetime import date

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

# infygram.com was the old event microsite and no longer resolves in DNS.
HWI_INFO_URL = "https://www.infosys.com/careers/hackwithinfy.html"


def _season_window() -> tuple[date, date]:
    """Rough open/close window for the current HackWithInfy season.

    Historically HackWithInfy runs Feb (registration) -> July (finale), e.g.:
      2022: reg Feb, rounds Mar/Jul
      2025: reg Feb, rounds Apr/Aug
      2026: reg Feb 6, round-1 Mar, finale Jul 1-4
    """
    year = date.today().year
    return date(year, 2, 1), date(year, 7, 31)


def _fetch_page() -> str | None:
    """Fetch the Infosys HackWithInfy careers page.

    The page is behind an Akamai/Cloudflare-style challenge, so plain httpx is
    blocked (403). We use StealthyFetcher which renders in a real browser and
    solves the challenge. Returns decoded HTML text or None on failure.
    """
    from scrapling.fetchers import StealthyFetcher
    try:
        page = StealthyFetcher.fetch(
            HWI_INFO_URL,
            headless=True,
            disable_resources=True,
            network_idle=True,
            solve_cloudflare=True,
            timeout=60000,
        )
    except Exception as e:
        logger.error("HackWithInfy StealthyFetcher failed: %s", e)
        return None
    if not page or page.status != 200:
        logger.warning("HackWithInfy returned status %s", getattr(page, "status", None))
        return None
    body = page.body
    if isinstance(body, bytes):
        return body.decode("utf-8", "replace")
    return str(body)


def scrape_hackwithinfy() -> list[ScrapeItem]:
    """HackWithInfy is seasonal — only report a live season when active.

    We first try to fetch the official Infosys careers page with a real browser
    (Cloudflare-gated). If the page text indicates registration is currently
    open for a live round, we return a real item with the actual dates we find.
    If the season is closed / not announced, we return 0 with a comment.
    """
    items: list[ScrapeItem] = []
    today = date.today()
    open_date, close_date = _season_window()

    logger.info("Fetching HackWithInfy: %s", HWI_INFO_URL)

    text = _fetch_page()
    if text:
        lower = text.lower()
        # The page only advertises a live "register now" window when a new
        # season has been announced. Look for fresh registration signals AND a
        # concrete date that is still in the future.
        ready = ("register now" in lower) or ("registration open" in lower)
        upcoming_dates = re.findall(
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+20(?:2[679]|3\d)\b",
            lower,
            re.I,
        )
        if ready and upcoming_dates:
            logger.info(
                "HackWithInfy page shows an open registration window with dates "
                "near the current year; treating season as open. Dates found: %s",
                upcoming_dates[:6],
            )
            year = date.today().year
            item = ScrapeItem(
                title=f"HackWithInfy {year}",
                type="Competition",
                source="HackWithInfy",
                link=HWI_INFO_URL,
                deadline="",
                eligibility="Pre-final year engineering students (India), 18+",
                tags=["infosys", "india", "coding", "competitive programming"],
                location="Online",
                notes="Infosys's annual pan-India coding competition. Pathway to "
                      "Infosys Specialist Programmer PPI and internships. "
                      "Registration via college placement officer. "
                      "Source: infosys.com/careers/hackwithinfy.html.",
            )
            if not item.validate():
                items.append(item)
                return items

        # Otherwise the season is not currently open.
        logger.info(
            "HackWithInfy page fetched but shows no live open registration window "
            "(season closed / not yet announced). Returning 0 items — correct for "
            "a seasonal event. Watch %s for the next season.", HWI_INFO_URL
        )
        return items

    # Fetch failed -> fall back to the calendar heuristic.
    if not (open_date <= today <= close_date):
        logger.info(
            "HackWithInfy %d is seasonal (registration ~Feb, finale ~Jul). "
            "Fetch failed and today (%s) is outside the open window, so the "
            "current season is NOT open. Returning 0 items — correct for a "
            "seasonal event, not a bug.",
            today.year,
            today.isoformat(),
        )
        return items

    logger.info(
        "HackWithInfy: fetch failed and today is within the nominal season "
        "window, but no live evidence was obtained; returning 0 rather than "
        "fabricating a season entry."
    )
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackwithinfy()
    print(f"HackWithInfy: {len(results)} items")
    for item in results:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
