"""
Microsoft Careers scraper.
Scrapes Microsoft's career page for internship roles.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

MS_WIDGETS = "https://careers.microsoft.com/widgets"
MS_SEARCH = "https://jobs.careers.microsoft.com/global/en/search?q=intern"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

PAYLOAD = {
    "lang": "en_us",
    "deviceType": "desktop",
    "country": "us",
    "ddoKey": "refineSearch",
    "sortBy": "",
    "subsearch": "",
    "from": 0,
    "jobs": "true",
    "counts": "true",
    "all_fields": ["country", "state", "city", "category", "employmentType"],
    "pageName": "search-results",
    "size": 100,
    "keywords": "intern",
    "global": "true",
    "selected_fields": {},
    "sort": "null",
    "locationData": {},
}


def scrape_microsoft_careers() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Microsoft Careers")

    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            # Grab session cookie from search page
            client.get("https://careers.microsoft.com/us/en/")
            resp = client.post(MS_WIDGETS, json=PAYLOAD)
            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])
                seen = set()
                for job in jobs:
                    title = job.get("title", "")
                    job_id = job.get("jobId", "")
                    if not title or job_id in seen:
                        continue
                    seen.add(job_id)
                    title_lower = title.lower()
                    if "intern" not in title_lower:
                        continue
                    props = job.get("properties", [])
                    location = next((p.get("value", "") for p in props if p.get("name") == "Location"), "")
                    link = job.get("externalUrl", f"https://jobs.careers.microsoft.com/global/en/job/{job_id}")

                    item = ScrapeItem(
                        title=f"[Microsoft] {title}", type="Internship", source="Microsoft Careers",
                        link=link, deadline="", eligibility="Students and recent graduates; global",
                        tags=["microsoft", "internship", "swe", "tech"], location=location or "Various",
                        organizer="Microsoft", notes="Source: jobs.careers.microsoft.com.",
                    )
                    if not item.validate():
                        items.append(item)
    except Exception as e:
        logger.error("Microsoft Careers request failed: %s", e)

    if not items:
        item = ScrapeItem(title="Microsoft Internships", type="Internship", source="Microsoft Careers", link=MS_SEARCH, deadline="", eligibility="Students and recent graduates; global", tags=["microsoft", "internship", "swe", "tech"], location="Various", organizer="Microsoft", notes="Visit link for current openings. Source: jobs.careers.microsoft.com.")
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