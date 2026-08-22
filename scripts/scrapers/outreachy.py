"""
Outreachy scraper.
Outreachy provides internships in free and open source software.
The internships page lists current and upcoming rounds.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

OUTREACHY_URL = "https://www.outreachy.org/apply/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_outreachy() -> list[ScrapeItem]:
    """Scrape Outreachy internship rounds."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Outreachy: %s", OUTREACHY_URL)

    try:
        resp = httpx.get(
            OUTREACHY_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Outreachy request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Outreachy returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=OUTREACHY_URL)

    # Look for round sections or links
    sections = page.css("section, .internship-round, .round, article, div[class*='round']")
    seen_links = set()

    for section in sections:
        link_el = section.css("a[href*='internship'], a[href*='apply']")
        title_el = section.css("h2, h3, h4, .title")
        deadline_el = section.css(".deadline, time, [class*='date'], [class*='deadline']")

        title = clean_text(title_el[0].text) if title_el else ""
        if not title:
            continue

        href = ""
        if link_el:
            href = link_el[0].attrib.get("href", "")

        deadline_raw = clean_text(deadline_el[0].text) if deadline_el else ""
        deadline = parse_deadline(deadline_raw)

        if href and not href.startswith("http"):
            href = f"https://www.outreachy.org{href}"

        if href in seen_links:
            continue
        seen_links.add(href)

        item = ScrapeItem(
            title=f"Outreachy {title}",
            type="Internship",
            source="Outreachy",
            link=href or OUTREACHY_URL,
            deadline=deadline,
            eligibility="Open source applicants; focus on underrepresented groups in tech",
            tags=["internship", "open source", "outreachy", "diversity"],
            location="Remote",
            notes="Paid internship in free and open source software. 3-month internships with stipend. Source: outreachy.org.",
        )
        if not item.validate():
            items.append(item)

    # Fallback: create general entry if no rounds found
    if not items:
        item = ScrapeItem(
            title="Outreachy Internships",
            type="Internship",
            source="Outreachy",
            link=OUTREACHY_URL,
            deadline="",
            eligibility="Open source applicants; focus on underrepresented groups in tech",
            tags=["internship", "open source", "outreachy", "diversity"],
            location="Remote",
            notes="Paid internship in free and open source software. Check site for current rounds. Source: outreachy.org.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Outreachy: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_outreachy()
    print(f"Outreachy: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
