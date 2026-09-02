"""
Outreachy scraper.
Outreachy provides paid, remote internships in free and open source software,
running two cohorts a year (May-Aug and Dec-Mar).

The official Applicant Guide page (outreachy.org/docs/applicant/) documents the
CURRENT round's schedule. As of Sep 2026 that is the December 2026 cohort:
  - Final application deadline: Nov. 2, 2026
  - Internships period: Dec. 7, 2026 - March 8, 2027
The final application deadline is still in the future, so the current round is
OPEN and we return one real item with the real deadline from the official page.
"""

from __future__ import annotations

import logging
import re
from datetime import date

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

OUTREACHY_URL = "https://www.outreachy.org/docs/applicant/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_round_label(text: str) -> str:
    """Extract the cohort label, e.g. 'December 2026 to March 2027'."""
    m = re.search(
        r"(?:December|May|June|March|February|January)\s+20\d{2}\s+to\s+\w+\s+20\d{2}",
        text,
        re.I,
    )
    return m.group(0) if m else ""


def scrape_outreachy() -> list[ScrapeItem]:
    """Scrape the current Outreachy internship round.

    Parses the official Applicant Guide page for a round whose final application
    deadline is still in the future (i.e. currently open) and returns one real
    item with the real deadline.
    """
    items: list[ScrapeItem] = []
    logger.info("Fetching Outreachy: %s", OUTREACHY_URL)

    try:
        resp = httpx.get(
            OUTREACHY_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Outreachy request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Outreachy returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=OUTREACHY_URL)
    text = page.get_all_text() or ""
    # Collapse whitespace (and stray tags) so dates separated by line breaks,
    # like "Nov. 2, 2026<at>4pm UTC", become matchable on a single line.
    text = re.sub(r"<[^>]+>", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)

    # Find the current/next round's final application deadline and internship period.
    # Applicant Guide pages render dates as e.g.
    #   "Nov. 2, 2026 at 4pm UTC Final application deadline"
    #   "Dec. 7, 2026 to March 8, 2027 Internships period"
    # i.e. the date(s) PRECEDE the label.
    dl_match = re.search(
        r"([A-Z][a-z]{2,8}\.?\s*\d{1,2},?\s*20\d{2})\s+at\s+\d{1,2}(?::\d{2})?\s*[ap]m\s*UTC\s+Final application deadline",
        text,
        re.I,
    )
    if not dl_match:
        logger.info(
            "Outreachy: could not find a current-round final application deadline "
            "on the official page. Returning 0."
        )
        return items

    raw_dl = dl_match.group(1)
    deadline = parse_deadline(raw_dl)
    if not deadline:
        logger.info("Outreachy: found deadline text '%s' but could not parse it.", raw_dl)
        return items

    today = date.today()
    if deadline < today.isoformat():
        logger.info(
            "Outreachy: the current round's final application deadline (%s) has "
            "already passed and the next round is not announced yet. Returning 0.",
            deadline,
        )
        return items

    period_match = re.search(
        r"([A-Z][a-z]{2,8}\.?\s*\d{1,2},?\s*20\d{2})\s+to\s+([A-Z][a-z]{2,8}\.?\s*\d{1,2},?\s*20\d{2})\s+Internships period",
        text,
        re.I,
    )    # Build a human round label from the internship start, e.g. "December 2026".
    start_label = ""
    if period_match:
        start = period_match.group(1)
        mm = re.match(r"([A-Z][a-z]{2,8})\.?\s*\d{1,2},?\s*(20\d{2})", start, re.I)
        if mm:
            month_full = {
                "jan": "January", "feb": "February", "mar": "March", "apr": "April",
                "may": "May", "jun": "June", "jul": "July", "aug": "August",
                "sep": "September", "oct": "October", "nov": "November", "dec": "December",
            }.get(mm.group(1).lower()[:3], mm.group(1))
            start_label = f"{month_full} {mm.group(2)}"
    round_label = start_label or "current"
    period = f"{period_match.group(1)} to {period_match.group(2)}" if period_match else ""

    notes = ["Source: Outreachy."]
    if period:
        notes.append(f"Internships: {period}.")
    notes.append("Paid, remote internship in free and open source software.")

    item = ScrapeItem(
        title=f"Outreachy {round_label}",
        type="Internship",
        source="Outreachy",
        link="https://www.outreachy.org/apply/",
        deadline=deadline,
        eligibility="Open-source applicants; focus on underrepresented groups in tech",
        tags=["internship", "open source", "outreachy", "diversity", "stipend"],
        location="Remote",
        notes=" ".join(notes),
    )
    if not item.validate():
        items.append(item)

    logger.info("Outreachy: scraped %d items (deadline=%s)", len(items), deadline)
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_outreachy()
    print(f"Outreachy: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
