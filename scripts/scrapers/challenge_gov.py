"""
Challenge.gov scraper.
Scrapes Challenge.gov for federal prize competitions and challenges.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
CHALLENGE_API = "https://api.challenge.gov/challenges/?status=open&limit=25"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_challenge_gov() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Challenge.gov")
    try:
        resp = httpx.get(CHALLENGE_API, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("Challenge.gov failed: %s", e)
        return items

    if resp.status_code == 200:
        try:
            data = resp.json()
            for ch in data.get("results", []):
                title = ch.get("title", "")
                url = ch.get("external_url", "") or f"https://www.challenge.gov/challenge/{ch.get('id', '')}/"
                agency = ch.get("agency", "")
                deadline = (ch.get("end_date", "") or "")[:10]
                if not title:
                    continue
                tags = ["challenge", "prize", "government", "federal"]
                agency_tag = agency.lower().replace(" ", "_") if agency else ""
                if agency_tag:
                    tags.append(agency_tag)
                items.append(ScrapeItem(title=f"[Challenge.gov] {title}", type="Competition", source="Challenge.gov", link=url, deadline=deadline, eligibility="Open to public; varies by challenge", tags=tags, location="Online", organizer=agency, notes="Federal prize competition. Source: challenge.gov."))
        except Exception:
            pass

    if not items:
        items.append(ScrapeItem(title="Federal Challenges & Prizes", type="Competition", source="Challenge.gov", link="https://www.challenge.gov/", deadline="", eligibility="Open to public", tags=["challenge", "prize", "government"], location="Online", notes="Visit link for current challenges."))
    items = deduplicate_by_link(items)
    logger.info("Challenge.gov: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_challenge_gov()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
