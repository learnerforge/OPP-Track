"""
IBM Skills Network scraper.
IBM offers certifications through ibm.com/training.
We parse the ibm.com/training/sitemap.xml for /certification/ URLs,
then extract title and description from each certification page's
HTML title and meta description tags.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

IBM_SITEMAP = "https://www.ibm.com/training/sitemap.xml"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html"}


def _get_cert_urls(limit: int = 50) -> list[str]:
    """Parse IBM sitemap for /certification/ URLs."""
    try:
        resp = httpx.get(IBM_SITEMAP, timeout=20, follow_redirects=True, headers=HEADERS)
        if resp.status_code != 200:
            logger.warning("IBM sitemap returned %d", resp.status_code)
            return []
        urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
        cert_urls = [u for u in urls if "/certification/" in u]
        logger.info("IBM sitemap: %d certification URLs, using %d", len(cert_urls), min(limit, len(cert_urls)))
        return cert_urls[:limit]
    except Exception as e:
        logger.error("IBM sitemap fetch failed: %s", e)
        return []


def scrape_ibm_skills() -> list[ScrapeItem]:
    """Scrape IBM certifications from the sitemap."""
    items: list[ScrapeItem] = []
    logger.info("Fetching IBM certification URLs from sitemap")

    cert_urls = _get_cert_urls(limit=50)
    if not cert_urls:
        logger.warning("No IBM certification URLs from sitemap")
        return items

    for url in cert_urls:
        try:
            resp = httpx.get(url, timeout=20, follow_redirects=True, headers=HEADERS)
            if resp.status_code != 200:
                continue

            html = resp.text

            title = ""
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html)
            if title_match:
                title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
                title = re.sub(r"\s*\|\s*IBM Training Certification\s*$", "", title)
            if not title:
                continue

            description = ""
            desc_match = re.search(
                r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html
            )
            if desc_match:
                description = clean_text(desc_match.group(1))

            tags = ["ibm", "certification"]
            title_lower = title.lower()
            if "security" in title_lower:
                tags.append("security")
            if "ai" in title_lower or "watson" in title_lower:
                tags.append("ai")
            if "cloud" in title_lower:
                tags.append("cloud")
            if "data" in title_lower:
                tags.append("data science")
            if "hashicorp" in title_lower:
                tags.append("hashicorp")

            notes_parts = ["Source: IBM Training."]
            if description:
                notes_parts.append(description[:200])

            item = ScrapeItem(
                title=title,
                type="Certification",
                source="IBM Skills",
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
            logger.debug("IBM cert page fetch failed for %s: %s", url, e)

    items = deduplicate_by_link(items)
    logger.info("IBM Skills: scraped %d certifications", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_ibm_skills()
    print(f"IBM Skills: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:60]}")
