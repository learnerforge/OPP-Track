"""
edX scraper.
edX offers university courses and MicroMasters programs.
The browse page at edx.org/browse lists available courses and programs.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

EDX_URL = "https://www.edx.org/browse"
EDX_BASE = "https://www.edx.org"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _try_api() -> list[dict]:
    """Try fetching courses from edX discovery API."""
    try:
        resp = httpx.get(
            "https://discovery.edx.org/api/v1/course_runs/?limit=50&ordering=-start",
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                return results
    except Exception as e:
        logger.debug("edX API failed: %s", e)
    return []


def scrape_edx() -> list[ScrapeItem]:
    """Scrape edX courses and programs."""
    items: list[ScrapeItem] = []
    logger.info("Fetching edX courses: %s", EDX_URL)

    # Try API first
    api_data = _try_api()
    if api_data:
        logger.info("edX API: %d results", len(api_data))
        for entry in api_data[:100]:
            if not isinstance(entry, dict):
                continue

            title = entry.get("title", "").strip()
            if not title:
                continue

            course_id = entry.get("id", "")
            course_key = entry.get("key", "")
            marketing_url = entry.get("marketing_url", "")

            link = marketing_url or f"{EDX_BASE}/course/{course_key}" if course_key else ""

            # Parse start date
            start_date = entry.get("start", "")
            deadline = parse_deadline(start_date) if start_date else ""

            # Get organization
            org = entry.get("organization", "")
            if not org:
                # Try to extract from course_key (e.g., "MITx/6.00.1x/1")
                if "/" in course_key:
                    org = course_key.split("/")[0]

            tags = ["online course", "mooc"]
            if org:
                tags.append(org.lower())

            # Level
            level = entry.get("level_type", "")
            if level:
                tags.append(level.lower())

            notes_parts = ["Source: edX."]
            if org:
                notes_parts.append(f"Provider: {org}.")

            item = ScrapeItem(
                title=title,
                type="Certification",
                source="edX",
                link=link,
                deadline=deadline,
                eligibility="Global participants",
                tags=tags,
                location="Online",
                notes=" ".join(notes_parts),
            )
            if not item.validate():
                items.append(item)
    else:
        # Fallback: scrape HTML
        try:
            resp = httpx.get(
                EDX_URL,
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            )
            if resp.status_code != 200:
                logger.warning("edX returned %d", resp.status_code)
                return items

            from scrapling import Selector
            page = Selector(resp.text, url=EDX_URL)

            cards = page.css(".product-card, .card, [class*='course'], article")
            seen_links = set()

            for card in cards:
                link_el = card.css("a[href*='/course'], a[href*='/program']")
                if not link_el:
                    continue

                href = link_el[0].attrib.get("href", "")
                title_el = card.css("h2, h3, h4, .title, [class*='title']")
                title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

                if not title or len(title) < 5:
                    continue

                full_url = href if href.startswith("http") else f"{EDX_BASE}{href}"
                if full_url in seen_links:
                    continue
                seen_links.add(full_url)

                # Get provider
                provider_el = card.css("[class*='provider'], [class*='institution'], [class*='partner']")
                provider = clean_text(provider_el[0].text) if provider_el else ""

                tags = ["online course", "mooc"]
                if provider:
                    tags.append(provider.lower())

                notes_parts = ["Source: edX."]
                if provider:
                    notes_parts.append(f"Provider: {provider}.")

                item = ScrapeItem(
                    title=title,
                    type="Certification",
                    source="edX",
                    link=full_url,
                    deadline="",
                    eligibility="Global participants",
                    tags=tags,
                    location="Online",
                    notes=" ".join(notes_parts),
                )
                if not item.validate():
                    items.append(item)
        except Exception as e:
            logger.error("edX request failed: %s", e)

    items = deduplicate_by_link(items)
    logger.info("edX: scraped %d courses", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_edx()
    print(f"edX: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
