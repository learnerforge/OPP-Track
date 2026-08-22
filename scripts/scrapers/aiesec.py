"""
AIESEC scraper.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, deduplicate_by_link

logger = logging.getLogger(__name__)
AIESEC_API = "https://shop.aiesec.org/graphql"
AIESEC_URL = "https://shop.aiesec.org/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
QUERY = """query { opportunities(default: { limit: 20, page: 1 }, filter: { basic: { programme: [GLOBAL_TALENT] } }) { total data { id title url programme } } }"""


def scrape_aiesec() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching AIESEC")
    try:
        resp = httpx.post(AIESEC_API, json={"query": QUERY}, timeout=30, headers={"User-Agent": UA, "Content-Type": "application/json"})
        if resp.status_code == 200:
            data = resp.json()
            for opp in data.get("data", {}).get("opportunities", {}).get("data", []):
                title = opp.get("title", "")
                url = opp.get("url", "")
                if not title:
                    continue
                if url and not url.startswith("http"):
                    url = f"https://shop.aiesec.org{url}"
                items.append(ScrapeItem(title=f"[AIESEC] {title}", type="Internship", source="AIESEC", link=url or AIESEC_URL, deadline="", eligibility="Students aged 18-30; global", tags=["aiesec", "global", "internship", "volunteer", "leadership"], location="Various", notes="AIESEC global talent program."))
    except Exception as e:
        logger.error("AIESEC API failed: %s", e)

    if not items:
        items.append(ScrapeItem(title="AIESEC Global Opportunities", type="Internship", source="AIESEC", link=AIESEC_URL, deadline="", eligibility="Students aged 18-30; global", tags=["aiesec", "global", "internship"], location="Various", notes="Visit link for current opportunities."))
    items = deduplicate_by_link(items)
    logger.info("AIESEC: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_aiesec()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
