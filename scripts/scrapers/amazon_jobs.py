"""
Amazon Jobs scraper.
Scrapes Amazon's public job search JSON API for internship roles.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

AMAZON_SEARCH_API = "https://www.amazon.jobs/en/search.json"
AMAZON_JOBS_URL = "https://www.amazon.jobs/en/search?base_query=intern&result_limit=40&sort=relevant"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_amazon_jobs() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Amazon Jobs")

    try:
        resp = httpx.get(
            AMAZON_SEARCH_API,
            params={"base_query": "intern", "result_limit": 100, "sort": "relevant"},
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Amazon Jobs request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Amazon Jobs returned %d", resp.status_code)
        item = ScrapeItem(
            title="Amazon Internships", type="Internship", source="Amazon Jobs",
            link=AMAZON_JOBS_URL, deadline="",
            eligibility="Students and recent graduates; global",
            tags=["amazon", "internship", "swe", "tech"],
            location="Various", organizer="Amazon",
            notes="Visit link to search current openings. Source: amazon.jobs.",
        )
        if not item.validate():
            items.append(item)
        return items

    try:
        data = resp.json()
    except Exception as e:
        logger.error("Amazon Jobs: invalid JSON: %s", e)
        return items

    jobs = data.get("jobs", []) or []
    seen = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        title = clean_text(job.get("title", ""))
        if not title:
            continue
        job_path = job.get("job_path", "") or ""
        if not job_path:
            continue
        link = f"https://www.amazon.jobs{job_path}" if job_path.startswith("/") else job_path
        if link in seen:
            continue
        seen.add(link)

        city = clean_text(job.get("city", ""))
        country = clean_text(job.get("country_code", ""))
        loc_raw = clean_text(job.get("location", ""))  # e.g. "MX, DIF, Mexico City"
        location = loc_raw or (f"{city}, {country}" if city or country else "")

        category = clean_text(job.get("business_category", ""))
        tags = ["amazon", "internship", "careers", "tech"]
        if category:
            tags.append(category.lower())

        item = ScrapeItem(
            title=f"[Amazon] {title}",
            type="Internship",
            source="Amazon Jobs",
            link=link,
            deadline="",
            eligibility="Students and recent graduates; global",
            tags=tags,
            location=location or "Various",
            organizer="Amazon",
            notes="Source: amazon.jobs public API.",
        )
        if not item.validate():
            items.append(item)

    if not items:
        item = ScrapeItem(
            title="Amazon Internships", type="Internship", source="Amazon Jobs",
            link=AMAZON_JOBS_URL, deadline="",
            eligibility="Students and recent graduates; global",
            tags=["amazon", "internship", "swe", "tech"],
            location="Various", organizer="Amazon",
            notes="Visit link for current openings. Source: amazon.jobs.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Amazon Jobs: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_amazon_jobs()
    print(f"Amazon Jobs: {len(results)} items")
    for item in results[:15]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:60]}")
