"""
Microsoft Careers scraper.
Scrapes Microsoft's career page for internship roles.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

MS_API = "https://gcsservices.careers.microsoft.com/search/api/v1/search?q=intern&pg=1&pgSz=20&o=Relevance&flt=true"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_microsoft_careers() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Microsoft Careers")

    try:
        resp = httpx.get(MS_API, timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    except Exception as e:
        logger.error("Microsoft Careers request failed: %s", e)
        return items

    if resp.status_code == 200:
        try:
            data = resp.json()
            jobs = data.get("operationResult", {}).get("result", {}).get("jobs", [])
            seen = set()
            for job in jobs:
                title = job.get("title", "")
                job_id = job.get("jobId", "")
                if not title or job_id in seen:
                    continue
                seen.add(job_id)
                title_lower = title.lower()
                if "intern" not in title_lower and "new grad" not in title_lower:
                    continue
                location = job.get("primaryWorkLocation", "")
                link = job.get("url", f"https://jobs.careers.microsoft.com/global/en/job/{job_id}")

                item = ScrapeItem(
                    title=f"[Microsoft] {title}", type="Internship", source="Microsoft Careers",
                    link=link, deadline="", eligibility="Students and recent graduates; global",
                    tags=["microsoft", "internship", "swe", "tech"], location=location or "Various",
                    organizer="Microsoft", notes="Source: jobs.careers.microsoft.com.",
                )
                if not item.validate():
                    items.append(item)
        except Exception:
            pass

    if not items:
        item = ScrapeItem(title="Microsoft Internships", type="Internship", source="Microsoft Careers", link="https://jobs.careers.microsoft.com/global/en/search?q=intern", deadline="", eligibility="Students and recent graduates; global", tags=["microsoft", "internship", "swe", "tech"], location="Various", organizer="Microsoft", notes="Visit link for current openings. Source: jobs.careers.microsoft.com.")
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Microsoft Careers: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_microsoft_careers()
    print(f"Microsoft Careers: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
