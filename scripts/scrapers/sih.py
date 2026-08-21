"""
Smart India Hackathon (SIH) scraper.
SIH is an annual government hackathon by MoE Innovation Cell.
The site at sih.gov.in is server-rendered (Bootstrap/jQuery).
The problem statements page lists challenges by ministry/department.
"""

from __future__ import annotations

import logging
import re

import httpx
from scrapling import Selector

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

SIH_BASE = "https://sih.gov.in"
SIH_PS_URL = f"{SIH_BASE}/sih2025PS"
SIH_HOME_URL = SIH_BASE


def _extract_problems_from_html(html: str) -> list[dict]:
    """Extract problem statements from SIH problem statements page."""
    page = Selector(html, url=SIH_PS_URL)
    problems: list[dict] = []

    # Look for table rows (SIH uses DataTables)
    rows = page.css("table tbody tr")
    if rows:
        for row in rows:
            cells = row.css("td")
            if len(cells) >= 4:
                title = cells[1].text.strip() if len(cells) > 1 else ""
                org = cells[2].text.strip() if len(cells) > 2 else ""
                category = cells[3].text.strip() if len(cells) > 3 else ""
                link_el = row.css("a")
                link = ""
                if link_el:
                    href = link_el[0].attrib.get("href", "")
                    if href.startswith("/"):
                        link = f"{SIH_BASE}{href}"
                    elif href.startswith("http"):
                        link = href

                if title and len(title) > 5:
                    problems.append({
                        "title": title,
                        "org": org,
                        "category": category,
                        "link": link,
                    })
        return problems

    # Fallback: look for card-based layout
    cards = page.css(".ps-card, .card, .problem-card, .ps-box")
    for card in cards:
        title_el = card.css("h3, h4, h5, .card-title, .ps-title")
        title = title_el[0].text.strip() if title_el else ""
        link_el = card.css("a")
        link = ""
        if link_el:
            href = link_el[0].attrib.get("href", "")
            if href.startswith("/"):
                link = f"{SIH_BASE}{href}"
            elif href.startswith("http"):
                link = href
        if title and len(title) > 5:
            problems.append({
                "title": title,
                "org": "",
                "category": "",
                "link": link,
            })

    return problems


def _extract_sih_info(html: str) -> dict:
    """Extract general SIH event info from the homepage."""
    page = Selector(html, url=SIH_HOME_URL)
    info: dict = {}

    # Look for timeline/dates
    text = page.text or ""
    # Try to find SIH 2026 dates
    date_match = re.search(r"SIH\s*2026.*?(\w+\s+\d{1,2})\s*[-–]\s*(\w+\s+\d{1,2})", text, re.IGNORECASE)
    if date_match:
        info["date_range"] = f"{date_match.group(1)} - {date_match.group(2)}"

    return info


def scrape_sih() -> list[ScrapeItem]:
    """Scrape Smart India Hackathon problem statements."""
    items: list[ScrapeItem] = []
    logger.info(f"Fetching SIH: {SIH_PS_URL}")

    try:
        resp = httpx.get(SIH_PS_URL, timeout=30, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
    except Exception as e:
        logger.error(f"SIH request failed: {e}")
        return items

    if resp.status_code != 200:
        logger.warning(f"SIH returned {resp.status_code}")
        return items

    problems = _extract_problems_from_html(resp.text)
    logger.info(f"SIH: found {len(problems)} problem statements")

    for prob in problems[:100]:  # Cap at 100
        title = prob["title"]
        link = prob["link"] or SIH_PS_URL
        org = prob["org"]
        category = prob["category"]

        notes_parts = ["Source: Smart India Hackathon 2025."]
        if org:
            notes_parts.append(f"Organization: {org}.")
        if category:
            notes_parts.append(f"Category: {category}.")

        tags = ["india", "government", "hackathon", "sih"]
        if category:
            tags.append(category.lower())

        item = ScrapeItem(
            title=title,
            type="Hackathon",
            source="Smart India Hackathon",
            link=link,
            deadline="",
            eligibility="College students (India)",
            tags=tags,
            location="India",
            notes=" ".join(notes_parts),
        )
        errors = item.validate()
        if not errors:
            items.append(item)

    # Also create a single entry for the SIH 2026 event itself
    sih_event = ScrapeItem(
        title="Smart India Hackathon 2026",
        type="Hackathon",
        source="Smart India Hackathon",
        link=SIH_BASE,
        deadline="",
        eligibility="College students (India)",
        tags=["india", "government", "hackathon", "sih", "sih2026"],
        location="India",
        notes="Annual government hackathon by MoE Innovation Cell. "
              "Institutes organize internal hackathons, then teams are nominated. "
              "Source: Smart India Hackathon.",
    )
    if not sih_event.validate():
        items.insert(0, sih_event)

    logger.info(f"SIH: scraped {len(items)} items total")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_sih()
    print(f"SIH: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
