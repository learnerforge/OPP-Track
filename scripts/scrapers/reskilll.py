"""
Reskilll scraper.
Scrapes Reskilll for Indian hackathons and contests.
"""

from __future__ import annotations
import logging
import httpx
from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)
RESKILL_URL = "https://reskilll.com/hackathons"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def scrape_reskilll() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Reskilll")
    try:
        resp = httpx.get(RESKILL_URL, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:
        logger.error("Reskilll failed: %s", e)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=RESKILL_URL)
    cards = page.css("article, .card, [class*='hack'], [class*='contest'], a[href]")
    seen = set()
    for card in cards:
        link_el = card.css("a[href]")
        if not link_el:
            continue
        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)
        if not title or len(title) < 3:
            continue
        full_url = href if href.startswith("http") else f"https://reskilll.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(ScrapeItem(title=f"[Reskilll] {title}", type="Hackathon", source="Reskilll", link=full_url, deadline="", eligibility="Students; India-focused", tags=["reskilll", "hackathon", "india", "contest"], location="Online", notes="Indian hackathon and contest platform. Source: reskilll.com."))

    if not items:
        items.append(ScrapeItem(title="Reskilll Hackathons", type="Hackathon", source="Reskilll", link=RESKILL_URL, deadline="", eligibility="Students; India-focused", tags=["reskilll", "hackathon", "india"], location="Online", notes="Visit link for current events."))
    items = deduplicate_by_link(items)
    logger.info("Reskilll: %d items", len(items))
    return items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for i in scrape_reskilll()[:10]:
        print(f"  {i.title[:60]} | {i.link[:50]}")
