"""
Buddy4Study scholarship scraper.
India's largest scholarship platform. Next.js app.
The scholarship listing page loads data client-side, but the __NEXT_DATA__
script contains SEO data and the site has an API at /api/scholarships.
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

B4S_BASE = "https://www.buddy4study.com"
B4S_LISTING_URL = f"{B4S_BASE}/scholarships"
B4S_API_URL = f"{B4S_BASE}/api/scholarships"


def _try_api() -> list[dict]:
    """Try fetching scholarships from the Buddy4Study API."""
    try:
        resp = httpx.get(
            B4S_API_URL,
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("scholarships", "data", "results", "items"):
                    if isinstance(data.get(key), list):
                        return data[key]
    except Exception as e:
        logger.debug(f"API failed: {e}")
    return []


def _try_next_data(html: str) -> list[dict]:
    """Try extracting scholarships from __NEXT_DATA__."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    props = data.get("props", {}).get("pageProps", data.get("props", {}))
    for key in ("scholarships", "data", "results", "items", "scholarshipList"):
        if isinstance(props.get(key), list):
            return props[key]
    return []


def _try_scholarship_categories(html: str) -> list[dict]:
    """Extract individual scholarship links from the HTML."""
    from scrapling import Selector
    page = Selector(html, url=B4S_LISTING_URL)
    scholarships = []

    # Look for any card-like elements
    cards = page.css("a[href*='/scholarship/']")
    seen = set()
    for card in cards:
        href = card.attrib.get("href", "")
        title = card.text.strip() if card.text else ""
        if not title or len(title) < 5:
            continue
        if title in seen:
            continue
        seen.add(title)
        full_url = href if href.startswith("http") else f"{B4S_BASE}{href}"
        scholarships.append({"title": title, "url": full_url})

    # Also try h2/h3 elements with scholarship-related links
    headings = page.css("h2 a, h3 a, h4 a")
    for h in headings:
        href = h.attrib.get("href", "")
        title = h.text.strip() if h.text else ""
        if not title or len(title) < 5 or title in seen:
            continue
        seen.add(title)
        full_url = href if href.startswith("http") else f"{B4S_BASE}{href}"
        scholarships.append({"title": title, "url": full_url})

    return scholarships


def scrape_buddy4study() -> list[ScrapeItem]:
    """Scrape Buddy4Study scholarships."""
    items: list[ScrapeItem] = []
    logger.info(f"Fetching Buddy4Study: {B4S_LISTING_URL}")

    # Try API first
    api_data = _try_api()
    if api_data:
        logger.info(f"Buddy4Study API: {len(api_data)} items")
        for entry in api_data[:200]:
            if not isinstance(entry, dict):
                continue
            title = entry.get("title", entry.get("name", "")).strip()
            if not title or len(title) < 5:
                continue
            link = entry.get("url", entry.get("link", entry.get("slug", "")))
            if link and not link.startswith("http"):
                link = f"{B4S_BASE}/scholarship/{link}" if not link.startswith("/") else f"{B4S_BASE}{link}"

            deadline = entry.get("deadline", entry.get("last_date", entry.get("endDate", "")))
            amount = entry.get("amount", entry.get("scholarship_amount", ""))
            provider = entry.get("provider", entry.get("organization", ""))

            notes_parts = ["Source: Buddy4Study."]
            if amount:
                notes_parts.append(f"Amount: {amount}.")
            if provider:
                notes_parts.append(f"Provider: {provider}.")

            item = ScrapeItem(
                title=title,
                type="Certification",
                source="Buddy4Study",
                link=link or B4S_LISTING_URL,
                deadline=deadline if deadline else "",
                eligibility="Indian students",
                tags=["india", "scholarship", "education"],
                location="India",
                notes=" ".join(notes_parts),
            )
            if not item.validate():
                items.append(item)
    else:
        # Fallback: scrape HTML
        try:
            resp = httpx.get(B4S_LISTING_URL, timeout=30, follow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            if resp.status_code == 200:
                # Try __NEXT_DATA__
                next_data = _try_next_data(resp.text)
                if next_data:
                    logger.info(f"Buddy4Study __NEXT_DATA__: {len(next_data)} items")
                    for entry in next_data[:200]:
                        if not isinstance(entry, dict):
                            continue
                        title = entry.get("title", entry.get("name", "")).strip()
                        if not title:
                            continue
                        link = entry.get("url", entry.get("slug", ""))
                        if link and not link.startswith("http"):
                            link = f"{B4S_BASE}/scholarship/{link}" if not link.startswith("/") else f"{B4S_BASE}{link}"
                        item = ScrapeItem(
                            title=title,
                            type="Certification",
                            source="Buddy4Study",
                            link=link or B4S_LISTING_URL,
                            deadline=entry.get("deadline", entry.get("last_date", "")),
                            eligibility="Indian students",
                            tags=["india", "scholarship", "education"],
                            location="India",
                            notes="Source: Buddy4Study.",
                        )
                        if not item.validate():
                            items.append(item)
                else:
                    # Last resort: parse links
                    raw = _try_scholarship_categories(resp.text)
                    logger.info(f"Buddy4Study HTML links: {len(raw)} items")
                    for entry in raw[:200]:
                        item = ScrapeItem(
                            title=entry["title"],
                            type="Certification",
                            source="Buddy4Study",
                            link=entry.get("url", B4S_LISTING_URL),
                            deadline="",
                            eligibility="Indian students",
                            tags=["india", "scholarship", "education"],
                            location="India",
                            notes="Source: Buddy4Study.",
                        )
                        if not item.validate():
                            items.append(item)
        except Exception as e:
            logger.error(f"Buddy4Study request failed: {e}")

    logger.info(f"Buddy4Study: scraped {len(items)} scholarships")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_buddy4study()
    print(f"Buddy4Study: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
