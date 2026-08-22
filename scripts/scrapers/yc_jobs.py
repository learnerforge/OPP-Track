"""
Y Combinator Jobs scraper.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
YC_URL = "https://www.workatastartup.com/jobs"
YC_API = "https://api.workatastartup.com/v1/companies"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_yc_jobs() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching YC Jobs")

    # Try API
    try:
        resp = httpx.get(YC_API, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
        if resp.status_code == 200:
            data = resp.json()
            companies = data if isinstance(data, list) else data.get("companies", [])
            for co in companies:
                roles = co.get("roles", [])
                company_name = co.get("name", "")
                for role in roles:
                    title = role.get("title", "")
                    url = role.get("url", "")
                    if not title:
                        continue
                    tl = title.lower()
                    if "intern" not in tl and "new grad" not in tl:
                        continue
                    if url and not url.startswith("http"):
                        url = f"https://www.workatastartup.com/jobs"
                    items.append(ScrapeItem(title=f"[YC] {title} -- {company_name}", type="Internship", source="YC Jobs", link=url or YC_URL, deadline="", eligibility="Students and graduates; startups", tags=["yc", "y combinator", "startup", "internship"], location=role.get("location", "") or "Various", organizer=company_name, notes="Source: workatastartup.com."))
    except Exception as e:
        logger.error("YC API failed: %s", e)

    if not items:
        items.append(ScrapeItem(title="YC Startup Internships", type="Internship", source="YC Jobs", link=YC_URL, deadline="", eligibility="Students and graduates; startups", tags=["yc", "y combinator", "startup", "internship"], location="Various", notes="Visit link for current YC startup jobs."))
    items = deduplicate_by_link(items)
    logger.info("YC Jobs: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_yc_jobs()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
