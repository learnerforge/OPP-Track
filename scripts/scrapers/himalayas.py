"""
Himalayas scraper.
Himalayas is a remote job board with detailed company profiles.
Uses the public JSON API at https://himalayas.app/jobs/api
(the HTML site is Cloudflare-gated with 403).
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HIMALAYAS_API = "https://himalayas.app/jobs/api"
HIMALAYAS_BASE = "https://himalayas.app"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _build_link(job: dict) -> str:
    slug = job.get("companySlug", "")
    title_slug = job.get("title", "").lower().replace(" ", "-")
    title_slug = "".join(c for c in title_slug if c.isalnum() or c == "-")
    if slug:
        return f"{HIMALAYAS_BASE}/jobs/{slug}/{title_slug}"
    return f"{HIMALAYAS_BASE}/jobs"


def scrape_himalayas() -> list[ScrapeItem]:
    """Scrape Himalayas remote jobs via the public JSON API."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Himalayas API: %s", HIMALAYAS_API)

    all_jobs: list[dict] = []
    cursor = ""
    max_pages = 5

    for page_num in range(max_pages):
        url = f"{HIMALAYAS_API}?limit=50"
        if cursor:
            url += f"&cursor={cursor}"
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True, headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            })
        except Exception as e:
            logger.error("Himalayas request failed on page %d: %s", page_num + 1, e)
            break

        if resp.status_code != 200:
            logger.warning("Himalayas API returned %d", resp.status_code)
            break

        data = resp.json()
        jobs = data.get("jobs", [])
        all_jobs.extend(jobs)
        cursor = data.get("nextCursor", "")
        logger.info("  Page %d: %d jobs (total so far: %d)", page_num + 1, len(jobs), len(all_jobs))

        if not cursor or not jobs:
            break

    logger.info("Himalayas: fetched %d total jobs from API", len(all_jobs))

    seen_links = set()
    for job in all_jobs:
        if not isinstance(job, dict):
            continue

        title = clean_text(job.get("title", ""))
        if not title or len(title) < 3:
            continue

        link = _build_link(job)
        link_key = link.rstrip("/").lower()
        if link_key in seen_links:
            continue
        seen_links.add(link_key)

        company = clean_text(job.get("companyName", ""))
        emp_type = clean_text(job.get("employmentType", ""))
        locations = job.get("locationRestrictions", [])
        location_str = ", ".join(locations[:3]) if locations else "Remote"
        salary_min = job.get("minSalary")
        salary_max = job.get("maxSalary")
        currency = job.get("currency", "")
        salary_period = job.get("salaryPeriod", "")

        tags = ["remote", "jobs", "himalayas"]
        categories = job.get("categories", []) or []
        for cat in categories[:5]:
            cat_clean = clean_text(cat).lower().replace("-", " ")
            if cat_clean and cat_clean not in tags:
                tags.append(cat_clean)

        notes_parts = ["Remote jobs board. Source: himalayas.app."]
        if emp_type:
            notes_parts.append(f"Type: {emp_type}.")
        if salary_min and salary_max:
            notes_parts.append(f"Salary: {currency} {salary_min}-{salary_max}/{salary_period}.")
        elif salary_min:
            notes_parts.append(f"Salary: {currency} {salary_min}/{salary_period}.")

        item = ScrapeItem(
            title=f"{title}" + (f" — {company}" if company else ""),
            type="Internship",
            source="Himalayas",
            link=link,
            deadline="",
            eligibility="Remote workers worldwide",
            tags=tags,
            location=location_str,
            organizer=company,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Himalayas: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_himalayas()
    print(f"Himalayas: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
