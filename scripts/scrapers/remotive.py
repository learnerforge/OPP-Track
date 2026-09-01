"""
Remotive scraper.
Remotive is a remote job board for tech roles.
Uses the public Remotive API (https://remotive.com/api/remote-jobs)
which returns live JSON jobs — the HTML site is Cloudflare-gated (403).
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

REMOTIVE_API = "https://remotive.com/api/remote-jobs?limit=50"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


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
        job_type = clean_text(job.get("job_type", ""))
        pub_date = clean_text(job.get("publication_date", ""))[:10]
        tags_raw = [clean_text(t) for t in (job.get("tags") or []) if clean_text(t)]

        tags = ["remote", "jobs"]
        if category:
            tags.append(category.lower())
        for t in tags_raw[:6]:
            if t and t.lower() not in [x.lower() for x in tags]:
                tags.append(t.lower())

        notes_parts = ["Curated remote tech jobs.", f"Category: {category}."] if category else ["Curated remote tech jobs."]
        if job_type:
            notes_parts.append(f"Employment type: {job_type}.")
        if pub_date:
            notes_parts.append(f"Posted: {pub_date}.")

        item = ScrapeItem(
            title=title + (f" — {company}" if company else ""),
            type="Internship",
            source="Remotive",
            link=full_url,
            deadline="",
            eligibility="Remote workers worldwide",
            tags=tags,
            location="Remote",
            organizer=company,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Remotive: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_remotive()
    print(f"Remotive: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")