"""
Smart India Hackathon (SIH) scraper.
SIH is an annual government hackathon by MoE Innovation Cell & AICTE.

As of Sep 2026 the SIH 2026 (9th edition) is LIVE: it was launched on
21 Aug 2026 with 229 problem statements, and the "Deadline for Idea
Submission" shown on the official problem-statements page is 20 September
2026. This scraper therefore returns the SIH 2026 event item with that real
date, scraped from sih.gov.in.
"""

from __future__ import annotations

import logging
import re

import httpx
from scrapling import Selector

from scripts.scrapers.base import ScrapeItem, parse_deadline

logger = logging.getLogger(__name__)

SIH_BASE = "https://sih.gov.in"
SIH_PS_URL = f"{SIH_BASE}/sih2026PS"


def _extract_idea_submission_deadline(html: str) -> str:
    """Extract the 'Deadline for Idea Submission' from the SIH problem
    statements DataTable.

    Each real data row has an 18th cell (last visible cell) holding the idea
    submission deadline, e.g. '20 September 2026'. We scan real rows and return
    the first well-formed date found.
    """
    page = Selector(html, url=SIH_PS_URL)
    rows = page.css("table tbody tr")
    seen: set[str] = set()
    for row in rows:
        cells = row.css("td")
        if len(cells) < 18:
            continue
        for c in cells[::-1]:
            raw = re.sub(r"\s+", " ", (c.text or "")).strip()
            if not raw:
                continue
            d = parse_deadline(raw)
            if d and d not in seen:
                seen.add(d)
                return d
    return ""


def scrape_sih() -> list[ScrapeItem]:
    """Scrape the current Smart India Hackathon edition.

    Returns the single SIH 2026 event item with the real idea-submission
    deadline parsed from sih.gov.in. Returns 0 if no live edition is found.
    """
    items: list[ScrapeItem] = []
    logger.info("Fetching SIH: %s", SIH_PS_URL)

    try:
        resp = httpx.get(SIH_PS_URL, timeout=30, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
    except Exception as e:
        logger.error("SIH request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("SIH returned %d", resp.status_code)
        return items

    deadline = _extract_idea_submission_deadline(resp.text)
    if not deadline:
        logger.info(
            "SIH: no live problem-statements page with an idea-submission deadline "
            "was found; the current edition may not be open. Returning 0."
        )
        return items

    event = ScrapeItem(
        title="Smart India Hackathon 2026",
        type="Hackathon",
        source="Smart India Hackathon",
        link=SIH_BASE,
        deadline=deadline,
        eligibility="College students (India) via institute SPOC; 6-member teams",
        tags=["india", "government", "hackathon", "sih", "sih2026"],
        location="India",
        notes="Annual government hackathon by MoE Innovation Cell & AICTE. "
              f"Idea submission due {deadline}; grand finale Dec 2026. "
              "Students participate through their institution's SPOC. "
              "Source: sih.gov.in/sih2026PS.",
    )
    if not event.validate():
        items.append(event)

    logger.info("SIH: scraped %d items (deadline=%s)", len(items), deadline)
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_sih()
    print(f"SIH: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
