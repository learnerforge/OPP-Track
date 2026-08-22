"""
SimplifyJobs scraper.
Scrapes the popular SimplifyJobs internship GitHub repo.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

README_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2025-Internships/dev/README.md"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_simplify_internships() -> list[ScrapeItem]:
    """Scrape SimplifyJobs internship repo from GitHub."""
    items: list[ScrapeItem] = []
    logger.info("Fetching SimplifyJobs internships from GitHub")

    try:
        resp = httpx.get(
            README_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("SimplifyJobs request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("SimplifyJobs returned %d", resp.status_code)
        return items

    lines = resp.text.split("\n")
    seen_links = set()

    for line in lines:
        link_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line)
        for link_text, href in link_matches:
            if "mailto:" in href:
                continue
            if not href.startswith("http"):
                continue

            if href in seen_links:
                continue
            seen_links.add(href)

            company = clean_text(link_text)
            if not company or len(company) < 2:
                continue

            line_lower = line.lower()
            if "intern" not in line_lower and "swe" not in line_lower:
                continue

            item = ScrapeItem(
                title=f"[SimplifyJobs] {company}",
                type="Internship",
                source="SimplifyJobs",
                link=href,
                deadline="",
                eligibility="Students and recent graduates",
                tags=["internship", "simplifyjobs", "curated"],
                location="Various",
                organizer=company,
                notes="From SimplifyJobs Summer Internships GitHub list.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("SimplifyJobs: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_simplify_internships()
    print(f"SimplifyJobs: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
