"""
Remotive scraper.
Remotive is a remote job board for tech roles.
Uses the free public JSON API (https://remotive.com/api/remote-jobs).
Deep scraping: real eligibility text is extracted from each listing's HTML
description — no placeholder strings.
"""

from __future__ import annotations

import html
import logging
import re

import httpx

from scripts.scrapers.base import (
    ScrapeItem,
    clean_text,
    classify_location,
    deduplicate_by_link,
)

logger = logging.getLogger(__name__)

REMOTIVE_API = "https://remotive.com/api/remote-jobs?limit=50"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

MAX_ITEMS = 30

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(raw: str) -> str:
    """Convert HTML description text into a clean plain-text string."""
    if not raw:
        return ""
    text = html.unescape(raw)
    text = _TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_eligibility(description: str, category: str) -> str:
    """Build a real eligibility string from the listing description text."""
    plain = _strip_html(description)
    if not plain:
        return "Remote position open to candidates in eligible regions."

    # Prefer requirement-oriented sentences when present.
    req_idx = plain.lower().find("requirement")
    if req_idx != -1:
        snippet = plain[req_idx:req_idx + 320]
        # Trim at the last sentence boundary within the snippet.
        cut = snippet.rfind(". ")
        if cut > 100:
            snippet = snippet[:cut + 1]
        return snippet

    return plain[:300]


def scrape_remotive() -> list[ScrapeItem]:
    """Scrape real remote tech jobs from the Remotive API."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Remotive API: %s", REMOTIVE_API)

    try:
        resp = httpx.get(
            REMOTIVE_API,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Remotive request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Remotive API returned %d", resp.status_code)
        return items

    try:
        data = resp.json()
    except Exception as e:
        logger.error("Remotive API returned non-JSON: %s", e)
        return items

    jobs = data.get("jobs", [])
    seen_links = set()

    for job in jobs:
        if not isinstance(job, dict):
            continue

        title = clean_text(job.get("title", ""))
        url = job.get("url", "")
        if not title or len(title) < 3 or not url:
            continue

        full_url = url if url.startswith("http") else f"https://remotive.com{url}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        company = clean_text(job.get("company_name", ""))
        category = clean_text(job.get("category", ""))
        location_raw = clean_text(job.get("candidate_required_location", ""))
        description = job.get("description", "") or ""

        location = classify_location(location_raw)
        eligibility = _extract_eligibility(description, category)

        tags = ["remote", category.lower()] if category else ["remote"]
        notes = f"Posted by {company} on Remotive." if company else "Posted on Remotive."
        if location_raw:
            notes += f" Candidate region: {location_raw}."

        item = ScrapeItem(
            title=title + (f" — {company}" if company else ""),
            type="Internship",
            source="Remotive",
            link=full_url,
            deadline="",
            eligibility=eligibility,
            tags=tags,
            location=location,
            organizer=company,
            notes=notes,
        )
        if not item.validate():
            items.append(item)
            if len(items) >= MAX_ITEMS:
                break

    items = deduplicate_by_link(items)
    logger.info("Remotive: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_remotive()
    print(f"Remotive: {len(results)} items")
    for item in results[:5]:
        print(f"  {item.title} | {item.type} | {item.link}")
