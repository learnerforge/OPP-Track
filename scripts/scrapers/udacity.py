"""
Udacity scraper.
Udacity offers Nanodegree programs and various courses from their catalog.
Catalog data is embedded as __NEXT_DATA__ JSON on /catalog, containing
hundreds of programs with titles, slugs, and descriptions.
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

UDACITY_CATALOG_URL = "https://www.udacity.com/catalog"
UDACITY_BASE = "https://www.udacity.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)

NANODEGREE_KEYS = {"nd002", "nd000", "nd089", "nd101", "nd018", "nd027", "nd098", "nd900"}


def _extract_catalog_items(resp_text: str) -> list[dict]:
    """Extract catalog search result items from the __NEXT_DATA__ payload."""
    match = NEXT_DATA_RE.search(resp_text)
    if not match:
        return []
    try:
        nd = json.loads(match.group(1))
        csr = (
            nd.get("props", {})
            .get("pageProps", {})
            .get("catalogSearchResults", {})
        )
        items = csr.get("searchResultItems", [])
        total_hits = csr.get("numberOfHits", 0)
        logger.info("Udacity catalog: %d total hits, %d on page 1", total_hits, len(items))
        return items
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Udacity __NEXT_DATA__ parse error: %s", e)
        return []


def scrape_udacity() -> list[ScrapeItem]:
    """Scrape Udacity nanodegree programs from the catalog."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Udacity catalog: %s", UDACITY_CATALOG_URL)

    try:
        resp = httpx.get(
            UDACITY_CATALOG_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Udacity request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Udacity returned %d", resp.status_code)
        return items

    catalog_items = _extract_catalog_items(resp.text)
    seen_links = set()

    for ci in catalog_items:
        title = (ci.get("title") or "").strip()
        slug = (ci.get("slug") or "").strip()
        key = (ci.get("key") or "").strip()
        summary = (ci.get("summary") or "").strip()

        if not title:
            continue

        link = f"{UDACITY_BASE}/course/{slug}" if slug else ""
        if not link:
            continue
        if link in seen_links:
            continue
        seen_links.add(link)

        tags = ["nanodegree", "online learning"]
        summary_lower = summary.lower()
        title_lower = title.lower()
        combined = f"{title_lower} {summary_lower}"

        if "ai" in combined or "artificial intelligence" in combined or "machine learning" in combined:
            tags.append("ai")
        if "data" in combined:
            tags.append("data science")
        if "python" in combined:
            tags.append("python")
        if "cloud" in combined or "aws" in combined:
            tags.append("cloud")
        if "security" in combined or "cybersecurity" in combined:
            tags.append("security")
        if "programming" in combined or "developer" in combined:
            tags.append("programming")
        if "marketing" in combined:
            tags.append("marketing")
        if "business" in combined:
            tags.append("business")

        notes_parts = ["Source: Udacity catalog."]
        if summary:
            notes_parts.append(summary[:200])

        item = ScrapeItem(
            title=title,
            type="Certification",
            source="Udacity",
            link=link,
            deadline="",
            eligibility="Global participants (18+)",
            tags=tags,
            location="Online",
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Udacity: scraped %d nanodegree programs", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_udacity()
    print(f"Udacity: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
