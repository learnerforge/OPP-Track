"""
edX scraper.
edX offers university courses and MicroMasters programs.
The browse page at edx.org/browse has been removed.
We parse the sitemap for /learn/ course URLs, then extract JSON-LD
structured data from each course page.
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

EDX_SITEMAP = "https://www.edx.org/sitemap.xml"
EDX_BASE = "https://www.edx.org"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}


def _get_course_urls(limit: int = 50) -> list[str]:
    """Parse edX sitemap for specific course URLs (/learn/<topic>/<provider>-<slug>)."""
    try:
        resp = httpx.get(EDX_SITEMAP, timeout=20, follow_redirects=True, headers=HEADERS)
        if resp.status_code != 200:
            logger.warning("edX sitemap returned %d", resp.status_code)
            return []
        urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
        courses = []
        for u in urls:
            m = re.match(r"https://www\.edx\.org/learn/([^/]+)/([^/]+)", u)
            if m and "/es/" not in u:
                courses.append(u)
        logger.info("edX sitemap: %d course URLs found, using %d", len(courses), min(limit, len(courses)))
        return courses[:limit]
    except Exception as e:
        logger.error("edX sitemap fetch failed: %s", e)
        return []


def _extract_jsonld_course(html: str) -> dict | None:
    """Extract Course JSON-LD from page HTML."""
    ld_blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    )
    for block in ld_blocks:
        try:
            data = json.loads(block)
            graph = data.get("@graph", [data])
            for item in graph:
                if item.get("@type") == "Course":
                    return item
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def scrape_edx() -> list[ScrapeItem]:
    """Scrape edX courses from sitemap + individual course pages."""
    items: list[ScrapeItem] = []
    logger.info("Fetching edX course URLs from sitemap")

    course_urls = _get_course_urls(limit=50)
    if not course_urls:
        logger.warning("No edX course URLs from sitemap")
        return items

    for url in course_urls:
        try:
            resp = httpx.get(url, timeout=20, follow_redirects=True, headers=HEADERS)
            if resp.status_code != 200:
                continue

            course = _extract_jsonld_course(resp.text)
            if not course:
                continue

            title = clean_text(course.get("name", ""))
            if not title:
                continue

            providers = course.get("provider", [])
            if isinstance(providers, dict):
                providers = [providers]
            org = providers[0].get("name", "") if providers else ""

            description = clean_text(course.get("description", ""))

            tags = ["online course", "mooc"]
            if org:
                tags.append(org.lower())

            notes_parts = ["Source: edX."]
            if org:
                notes_parts.append(f"Provider: {org}.")

            item = ScrapeItem(
                title=title,
                type="Certification",
                source="edX",
                link=url,
                deadline="",
                eligibility="Global participants",
                tags=tags,
                location="Online",
                notes=" ".join(notes_parts),
            )
            if not item.validate():
                items.append(item)
        except Exception as e:
            logger.debug("edX course fetch failed for %s: %s", url, e)

    items = deduplicate_by_link(items)
    logger.info("edX: scraped %d courses", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_edx()
    print(f"edX: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:60]}")
