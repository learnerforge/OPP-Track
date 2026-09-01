"""
MLH Fellowship scraper.
The MLH Fellowship is a 12-week, fully remote internship alternative that runs
year-round in batches (Spring / Summer / Fall).

As of Sep 2026:
  - The Fall 2026 batch (Sep 14 - Dec 4, 2026) had an application deadline of
    Aug 31, 2026, which has already passed.
  - The next batch (e.g. Spring 2027) has not been announced with a confirmed
    application deadline.
  - MLH does not currently match fellowship projects for applicants residing in
    India and many other Asia-Pacific countries (applications from those regions
    are accepted but closed without review).

Because there is no currently-open application window with a concrete, future
deadline, and because this is an India-focused tracker, this scraper returns 0
with a clear explanation rather than a fabricated entry.
"""

from __future__ import annotations

import logging
import re
from datetime import date

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline

logger = logging.getLogger(__name__)

MLH_FELLOWSHIP_URL = "https://fellowship.mlh.com/"
MLH_APPLY_URL = "https://fellowship.mlh.com/apply"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_mlh_fellowship() -> list[ScrapeItem]:
    """Scrape the current MLH Fellowship batch.

    Returns a real item only if the official page shows a batch application
    window still open (deadline in the future). Otherwise returns 0.
    """
    items: list[ScrapeItem] = []
    logger.info("Fetching MLH Fellowship: %s", MLH_FELLOWSHIP_URL)

    try:
        resp = httpx.get(
            MLH_FELLOWSHIP_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("MLH Fellowship request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("MLH Fellowship returned %d", resp.status_code)
        return items

    text = resp.text
    # Scan for a batch application deadline that is still in the future.
    deadline_found = ""
    for m in re.finditer(
        r"(?:application deadline|deadline for applicants)[:\s]*(?:all regions[:\s]*)?([A-Z][a-z]{2,8}\.?\s*\d{1,2},?\s*20\d{2})",
        text,
        re.I,
    ):
        d = parse_deadline(m.group(1))
        if d and d >= date.today().isoformat():
            deadline_found = d
            break

    if not deadline_found:
        logger.info(
            "MLH Fellowship: no openly-announced batch with a future application "
            "deadline was found (the Fall 2026 batch deadline of Aug 31, 2026 has "
            "passed and the next batch is not yet announced). Additionally MLH "
            "does not currently match projects for India-based applicants. "
            "Returning 0."
        )
        return items

    item = ScrapeItem(
        title="MLH Fellowship",
        type="Internship",
        source="MLH Fellowship",
        link=MLH_APPLY_URL,
        deadline=deadline_found,
        eligibility="Open-source developers; 18+; students and recent graduates; note MLH regional project limits",
        tags=["fellowship", "open source", "mlh", "internship", "stipend"],
        location="Remote",
        notes="12-week paid, remote fellowship. Verify the current batch dates and "
              "regional availability on fellowship.mlh.com/apply. Source: fellowship.mlh.com.",
    )
    if not item.validate():
        items.append(item)

    logger.info("MLH Fellowship: scraped %d items (deadline=%s)", len(items), deadline_found)
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_mlh_fellowship()
    print(f"MLH Fellowship: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
