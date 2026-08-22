"""
USAJobs scraper.
Scrapes USAJobs API for federal government internships.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, deduplicate_by_link

logger = logging.getLogger(__name__)
USAJOBS_API = "https://data.usajobs.gov/api/search?Keyword=intern&ResultsPerPage=25"
UA = "OPP-Track/1.0 (opportunity-tracker)"


def scrape_usajobs() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching USAJobs")
    try:
        resp = httpx.get(USAJOBS_API, timeout=30, follow_redirects=True, headers={"User-Agent": UA, "Host": "data.usajobs.gov"})
    except Exception as e:
        logger.error("USAJobs failed: %s", e)
        return items

    if resp.status_code == 200:
        try:
            data = resp.json()
            for job in data.get("SearchResult", {}).get("SearchResultItems", []):
                m = job.get("MatchedObjectDescriptor", {})
                title = m.get("PositionTitle", "")
                url = m.get("PositionURI", "")
                org = m.get("OrganizationName", "")
                locs = m.get("PositionLocation", [])
                loc = locs[0].get("CityName", "") if locs else ""
                pub = (m.get("PublicationStartDate", "") or "")[:10]
                if not title:
                    continue
                items.append(ScrapeItem(title=f"[USAJobs] {title}", type="Internship", source="USAJobs", link=url or "https://www.usajobs.gov/", deadline=pub, eligibility="US citizens; federal government", tags=["usa", "government", "internship", "federal"], location=loc or "USA", organizer=org, notes="Source: usajobs.gov."))
        except Exception:
            pass

    if not items:
        items.append(ScrapeItem(title="USAJobs Federal Internships", type="Internship", source="USAJobs", link="https://www.usajobs.gov/", deadline="", eligibility="US citizens; federal government", tags=["usa", "government", "internship"], location="USA", organizer="US Federal Government", notes="Visit link for current openings."))
    items = deduplicate_by_link(items)
    logger.info("USAJobs: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_usajobs()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
