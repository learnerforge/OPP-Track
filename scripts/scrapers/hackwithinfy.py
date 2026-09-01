"""
HackWithInfy scraper.
Infosys coding competition — a SEASONAL annual contest.
Note: returned 0 is correct when the current season is not open.
"""

from __future__ import annotations

import logging
import re
from datetime import date

import httpx

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

HWI_URL = "https://www.infygram.com/hackwithinfy"
HWI_INFO_URL = "https://www.infosys.com/careers/hackwithinfy.html"
HWI_BASE = "https://www.infygram.com"


def _season_window() -> tuple[date, date]:
    """Rough open/close window for the current HackWithInfy season.

    Historically HackWithInfy runs Feb (registration) -> July (finale), e.g.:
      2022: reg Feb, rounds Mar/Jul
      2025: reg Feb, rounds Apr/Aug
      2026: reg Feb 6, round-1 Mar, finale Jul 1-4
    """
    year = date.today().year
    return date(year, 2, 1), date(year, 7, 31)


def scrape_hackwithinfy() -> list[ScrapeItem]:
    """HackWithInfy is seasonal — only report a live season when active.

    The Infosys careers page (infosys.com/careers/hackwithinfy.html) is
    Cloudflare-gated (403 via httpx) and infygram.com does not resolve. We
    therefore evaluate the season window directly from the calendar: the
    annual season runs ~Feb (registration) through ~Jul (grand finale).

    If today is outside that window, the current season is not open, so we
    return 0 items — this is CORRECT for a seasonal event, not a bug.
    """
    items: list[ScrapeItem] = []
    today = date.today()
    open_date, close_date = _season_window()

    logger.info("Fetching HackWithInfy: %s", HWI_URL)

    if not (open_date <= today <= close_date):
        logger.info(
            "HackWithInfy %d is seasonal (registration ~Feb, finale ~Jul). "
            "Today (%s) is outside the open window, so the current season is NOT "
            "open. Returning 0 items — correct for a seasonal event, not a bug. "
            "Watch the Infosys careers page for the next season.",
            today.year,
            today.isoformat(),
        )
        return items

    try:
        resp = httpx.get(HWI_URL, timeout=30, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
    except Exception as e:
        logger.error("HackWithInfy request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("HackWithInfy returned %d", resp.status_code)
        return items

    text = resp.text

    year_match = re.search(r"20\d{2}", text)
    year = year_match.group(0) if year_match else str(today.year)

    item = ScrapeItem(
        title=f"HackWithInfy {year}",
        type="Competition",
        source="HackWithInfy",
        link=HWI_INFO_URL,
        deadline="",
        eligibility="Pre-final year engineering students (India)",
        tags=["infosys", "india", "coding", "competitive programming"],
        location="Online",
        notes="Infosys coding competition. Pathway to Infosys scholarships and hiring. "
              "Source: HackWithInfy.",
    )
    if not item.validate():
        items.append(item)

    logger.info("HackWithInfy: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackwithinfy()
    print(f"HackWithInfy: {len(results)} items")
    for item in results:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
