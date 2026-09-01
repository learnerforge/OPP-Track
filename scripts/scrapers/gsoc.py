"""
Google Summer of Code scraper.
GSoC is a global, annual program for students to contribute to open source.

GSoC is SEASONAL/ANNUAL. The scraper reads the official GSoC timeline page
(developers.google.com/open-source/gsoc/timeline) which lists the current
year's real "GSoC contributor application deadline". It returns a real item
with that real deadline only while the application window is still open (the
deadline is in the future). Otherwise it returns 0 — the current cycle's
application window has closed and the next cycle has not been announced.
No fabricated dates are ever injected.
"""

from __future__ import annotations

import logging
import re
from datetime import date

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline

logger = logging.getLogger(__name__)

GSOC_URL = "https://summerofcode.withgoogle.com/"
GSOC_TIMELINE_URL = "https://developers.google.com/open-source/gsoc/timeline"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _fetch_timeline_text() -> str | None:
    """Return the de-tagged text of the official GSoC timeline page."""
    try:
        resp = httpx.get(
            GSOC_TIMELINE_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("GSoC timeline request failed: %s", e)
        return None
    if resp.status_code != 200:
        logger.warning("GSoC timeline returned %d", resp.status_code)
        return None
    text = re.sub(r"<script.*?</script>", " ", resp.text, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def scrape_gsoc() -> list[ScrapeItem]:
    """Scrape Google Summer of Code info.

    Parses the official timeline for the current year's contributor application
    deadline. Returns a real item with that real deadline only when the
    deadline is still in the future; otherwise returns 0.
    """
    items: list[ScrapeItem] = []
    logger.info("Checking GSoC season: %s", GSOC_TIMELINE_URL)

    text = _fetch_timeline_text()
    if not text:
        return items

    # Current program year as labelled on the timeline, e.g. "2026 Timeline".
    year_match = re.search(r"\b(20\d{2})\s+Timeline\b", text)
    year = year_match.group(1) if year_match else str(date.today().year)

    # "March 31 - 18:00 UTC GSoC contributor application deadline"
    dl_match = re.search(
        r"([A-Z][a-z]{2,8}\.?\s*\d{1,2})\s*[-–]?\s*\d{1,2}:\d{2}\s*UTC\s*GSoC contributor application deadline",
        text,
        re.I,
    )
    if not dl_match:
        logger.info(
            "GSoC: could not locate the contributor application deadline on the "
            "official timeline. Returning 0 (no fabricated dates)."
        )
        return items

    raw = f"{dl_match.group(1)}, {year}"
    deadline = parse_deadline(raw)
    if not deadline:
        logger.info("GSoC: failed to parse applicant deadline '%s'. Returning 0.", raw)
        return items

    if deadline < date.today().isoformat():
        logger.info(
            "GSoC %s is seasonal: the contributor application deadline (%s) has "
            "already passed and the next cycle has not been announced. Returning 0 "
            "— correct for a seasonal program. Watch %s for the next cycle.",
            year, deadline, GSOC_TIMELINE_URL,
        )
        return items

    item = ScrapeItem(
        title=f"Google Summer of Code {year}",
        type="Internship",
        source="GSoC",
        link=GSOC_URL,
        deadline=deadline,
        eligibility="Students 18+ enrolled in or accepted to an accredited university; global",
        tags=["gsoc", "open source", "google", "internship", "stipend"],
        location="Remote",
        notes="12+ week paid program contributing to open source with a stipend. "
              "Application deadline from the official GSoC timeline. "
              "Source: developers.google.com/open-source/gsoc/timeline.",
    )
    if not item.validate():
        items.append(item)

    logger.info("GSoC: scraped %d items (deadline=%s)", len(items), deadline)
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_gsoc()
    print(f"GSoC: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
