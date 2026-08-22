"""
Remotive scraper.
Remotive is a remote job board for tech roles including internships.
The remote-jobs page lists curated remote positions.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

REMOTIVE_URL = "https://remotive.com/remote-jobs"
REMOTIVE_BASE = "https://remotive.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_remotive() -> list[ScrapeItem]:
    """Scrape Remotive remote tech jobs and internships."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Remotive: %s", REMOTIVE_URL)

    try:
        resp = httpx.get(
            REMOTIVE_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Remotive request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Remotive returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=REMOTIVE_URL)

    cards = page.css(".job-card, .card, [class*='job'], article, li[class*='job']")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/remote-jobs/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title'], [class*='name']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 3:
            continue

        # Filter for internships
        title_lower = title.lower()
        if "intern" not in title_lower and "apprentice" not in title_lower and "junior" not in title_lower:
            continue

        full_url = href if href.startswith("http") else f"{REMOTIVE_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        company_el = card.css("[class*='company'], [class*='employer'], .company-name")
        company = clean_text(company_el[0].text) if company_el else ""

        tags_els = card.css("[class*='tag'], .badge, .label")
        tags = ["remote", "internship", "tech"]
        for t in tags_els[:3]:
            tag_text = clean_text(t.text).lower()
            if tag_text:
                tags.append(tag_text)

        item = ScrapeItem(
            title=f"[Remotive] {title}" + (f" — {company}" if company else ""),
            type="Internship",
            source="Remotive",
            link=full_url,
            deadline="",
            eligibility="Remote workers worldwide",
            tags=list(set(tags)),
            location="Remote",
            organizer=company,
            notes="Curated remote tech jobs. Source: remotive.com.",
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
