"""
Google Careers scraper.
Scrapes Google's career page for internship and new grad roles.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

GOOGLE_JOBS_URL = "https://www.google.com/about/careers/applications/jobs/results/"
GOOGLE_API = "https://www.google.com/about/careers/api/jobs"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_google_careers() -> list[ScrapeItem]:
    """Scrape Google internships and new grad roles."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Google Careers")

    # Try API first
    try:
        resp = httpx.get(
            GOOGLE_API,
            params={"q": "intern", "sort_by": "relevance"},
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        if resp.status_code == 200:
            data = resp.json()
            jobs = data.get("jobs", [])
            seen = set()
            for job in jobs:
                title = job.get("title", "")
                if not title:
                    continue
                title_lower = title.lower()
                if "intern" not in title_lower and "new grad" not in title_lower and "graduate" not in title_lower:
                    continue

                job_id = job.get("job_id", "")
                if job_id in seen:
                    continue
                seen.add(job_id)

                location = job.get("location", "")
                team = job.get("team", "")
                link = f"https://www.google.com/about/careers/applications/jobs/results/{job_id}" if job_id else GOOGLE_JOBS_URL

                item = ScrapeItem(
                    title=f"[Google] {title}" + (f" — {team}" if team else ""),
                    type="Internship",
                    source="Google Careers",
                    link=link,
                    deadline="",
                    eligibility="Students and recent graduates; global",
                    tags=["google", "internship", "swe", "tech", "big tech"],
                    location=location or "Various",
                    organizer="Google",
                    notes="Source: google.com/about/careers.",
                )
                if not item.validate():
                    items.append(item)
    except Exception as e:
        logger.error("Google Careers API failed: %s", e)

    # Fallback: create entry pointing to search page
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
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
