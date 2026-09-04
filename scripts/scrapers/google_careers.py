"""
Google Careers scraper.
Scrapes Google's career page for internship and new grad roles.

The Google careers search page is a JS-rendered SPA: job data is fetched
client-side and embedded in AF_initDataCallback blocks. We render the page and
parse the "ds:1" AF_initDataCallback JSON which contains the job listings.
"""

from __future__ import annotations

import json
import logging
import re

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

GOOGLE_JOBS_URL = "https://www.google.com/about/careers/applications/jobs/results?q=intern"
GOOGLE_RESULTS = "https://www.google.com/about/careers/applications/jobs/results"


def _extract_balanced(text: str, start_idx: int):
    """Return (start, end) of balanced JSON array/object starting at start_idx."""
    i = start_idx
    while i < len(text) and text[i] in " \n\r\t":
        i += 1
    ch = text[i]
    open_ch = ch
    close_ch = "]" if ch == "[" else ("}" if ch == "{" else None)
    if close_ch is None:
        return None
    depth = 0
    in_str = False
    esc = False
    j = i
    while j < len(text):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return (i, j + 1)
        j += 1
    return None


def scrape_google_careers() -> list[ScrapeItem]:
    """Scrape Google internships and new grad roles."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Google Careers")

    from scrapling import StealthyFetcher

    try:
        page = StealthyFetcher.fetch(
            GOOGLE_JOBS_URL,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=45000,
        )
    except Exception as e:
        logger.error("Google Careers fetch failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("Google Careers returned %d", page.status)
        return items

    body = page.body
    text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)

    # Locate the ds:1 AF_initDataCallback block (contains job listings).
    idx = text.find("AF_initDataCallback({key: 'ds:1'")
    if idx < 0:
        idx = text.find("ds:1")
    data_start = text.find("data:", idx)
    span = _extract_balanced(text, data_start + len("data:")) if data_start >= 0 else None
    if span is None:
        logger.warning("Google Careers: could not locate job data block")
        return items

    raw = text[span[0]:span[1]]
    try:
        data = json.loads(raw)
    except Exception as e:
        logger.error("Google Careers: JSON parse error: %s", e)
        return items

    # top-level is a list whose first element is the list of jobs
    jobs = data[0] if isinstance(data, list) and data and isinstance(data[0], list) else data

    seen = set()
    for job in jobs:
        if not isinstance(job, list) or len(job) < 2:
            continue
        job_id = str(job[0] or "").strip()
        title = clean_text(job[1] or "")
        if not title or not job_id:
            continue
        if job_id in seen:
            continue
        seen.add(job_id)

        link = f"{GOOGLE_RESULTS}/{job_id}"

        # locations at index [9]: list of [display, addresses, city, zip, state, country] entries
        locations = job[9] if len(job) > 9 and isinstance(job[9], list) else []
        locs = []
        for loc in locations:
            if isinstance(loc, list) and loc and isinstance(loc[0], str) and loc[0]:
                locs.append(loc[0])
        location = ", ".join(dict.fromkeys(locs)) if locs else "Various"

        tags = ["google", "internship", "careers", "tech"]
        # new-grad / PhD variants
        tl = title.lower()
        if "phd" in tl:
            tags.append("phd")
        if "new grad" in tl or "early career" in tl:
            tags.append("new grad")

        item = ScrapeItem(
            title=f"[Google] {title}",
            type="Internship",
            source="Google Careers",
            link=link,
            deadline="",
            eligibility="Students and recent graduates; global",
            tags=tags,
            location=location,
            organizer="Google",
            notes="Source: google.com/about/careers.",
        )
        if not item.validate():
            items.append(item)

    if not items:
        item = ScrapeItem(
            title="Google Internships & New Grad",
            type="Internship",
            source="Google Careers",
            link=GOOGLE_JOBS_URL,
            deadline="",
            eligibility="Students and recent graduates; global",
            tags=["google", "internship", "swe", "tech", "big tech"],
            location="Various",
            organizer="Google",
            notes="Visit link to search for current openings. Source: google.com/about/careers.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Google Careers: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_google_careers()
    print(f"Google Careers: {len(results)} items")
    for item in results[:15]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:60]}")
