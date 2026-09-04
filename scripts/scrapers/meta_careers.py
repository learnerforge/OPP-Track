"""
Meta Careers scraper.
Scrapes Meta's public career page for internship roles.

Meta's careers site is a JS-rendered (Relay) app that blocks plain HTTP scrapers
(returns 400). We render it with StealthyFetcher and parse the rendered job
cards, extracting real internship postings.
"""

from __future__ import annotations

import logging
import re

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

META_URL = "https://www.metacareers.com/jobs?q=intern"


def _title_from_raw_h3(h3_html: str) -> str:
    """Extract clean title text from raw <h3> HTML, preserving spaces between spans."""
    # remove the opening/closing h3 tags and any nested tags; keep text+spaces
    inner = re.sub(r"<h3[^>]*>", "", h3_html)
    inner = re.sub(r"</h3>", "", inner)
    inner = re.sub(r"<[^>]+>", "", inner)
    inner = inner.replace("&amp;", "&").replace("&nbsp;", " ").replace("&quot;", '"')
    return clean_text(inner)


def scrape_meta_careers() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Meta Careers")

    from scrapling import StealthyFetcher
    from scrapling import Selector

    try:
        page = StealthyFetcher.fetch(
            META_URL, headless=True, disable_resources=True, network_idle=True, timeout=60000
        )
    except Exception as e:
        logger.error("Meta Careers fetch failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("Meta Careers returned %d", page.status)
        return items

    body = page.body
    text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
    sel = Selector(text, url=META_URL)

    seen = set()
    for a in sel.css('a[href*="/profile/job_details/"]'):
        href = a.attrib.get("href", "")
        if not href or href in seen:
            continue
        seen.add(href)
        link = f"https://www.metacareers.com{href}" if href.startswith("/") else href

        # title from the h3 inside the card (spans lose spaces via .text)
        h3 = a.css("h3")
        title = ""
        if h3:
            h3_html = str(h3[0].html_content) if hasattr(h3[0], "html_content") else str(h3[0])
            title = _title_from_raw_h3(h3_html)
        if not title:
            title = clean_text(a.text)

        # type label (e.g. "Internship - PhD") from spans inside the card
        label = ""
        for span in a.css("span"):
            st = clean_text(span.text)
            if st and "intern" in st.lower():
                label = st
                break

        tags = ["meta", "facebook", "internship", "careers", "tech"]
        tl = (title + " " + label).lower()
        if "phd" in tl:
            tags.append("phd")
        if "university" in tl or "university grad" in tl:
            tags.append("new grad")

        item = ScrapeItem(
            title=f"[Meta] {title}",
            type="Internship",
            source="Meta Careers",
            link=link,
            deadline="",
            eligibility="Students and recent graduates; global",
            tags=tags,
            location="Various",
            organizer="Meta",
            notes="Source: metacareers.com." + (f" ({label})" if label else ""),
        )
        if not item.validate():
            items.append(item)

    if not items:
        items.append(ScrapeItem(
            title="Meta Internships", type="Internship", source="Meta Careers", link=META_URL,
            deadline="", eligibility="Students and recent graduates; global",
            tags=["meta", "facebook", "internship"], location="Various", organizer="Meta",
            notes="Visit link for current openings.",
        ))
    items = deduplicate_by_link(items)
    logger.info("Meta Careers: %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_meta_careers()
    print(f"Meta Careers: {len(results)} items")
    for item in results[:20]:
        print(f"  {item.title[:65]} | {item.type} | {item.link[:60]}")
