"""
Buddy4Study scholarship scraper.
The listing page is a client-side Next.js app; the server-rendered HTML is an
SEO shell. We render it with StealthyFetcher and parse the scholarship cards
classes (Listing_* module CSS) emitted by the app.
"""

from __future__ import annotations

import logging
import re

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, clean_text, parse_deadline, deduplicate_by_link

logger = logging.getLogger(__name__)

B4S_BASE = "https://www.buddy4study.com"
B4S_LISTING_URL = f"{B4S_BASE}/scholarships"


def _abs_url(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return B4S_BASE + ("/" + href.lstrip("/") if href else "")


def _item_link(wrap) -> str:
    """Best link for an item: /scholarship/... or /page/... from logo/anchor."""
    for a in wrap.css("a"):
        h = (a.attrib.get("href") or "").strip()
        if "scholarship" in h or "/page/" in h:
            return _abs_url(h)
    for a in wrap.css("a"):
        h = (a.attrib.get("href") or "").strip()
        if h:
            return _abs_url(h)
    return ""


def scrape_buddy4study() -> list[ScrapeItem]:
    """Scrape live Buddy4Study scholarships for Indian students."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Buddy4Study (rendered): %s", B4S_LISTING_URL)

    try:
        page = StealthyFetcher.fetch(
            B4S_LISTING_URL,
            headless=True,
            disable_resources=False,
            network_idle=True,
            timeout=45000,
        )
    except Exception as e:
        logger.error("Buddy4Study StealthyFetcher failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("Buddy4Study returned status %d", page.status)
        return items

    name_els = page.css("h4[class*='scholarshipName']")
    if not name_els:
        logger.warning("Buddy4Study: no scholarship cards found in rendered HTML")
        return items

    seen_links = set()

    for nh in name_els:
        ps = nh.xpath("./following-sibling::p[1]")
        title = clean_text(ps[0].text) if ps else ""
        if not title or len(title) < 5:
            continue

        wrap = nh.xpath("parent::*")
        if not wrap:
            continue

        link = _item_link(wrap[0])
        if not link:
            continue
        link_key = link.rstrip("/").lower()
        if link_key in seen_links:
            continue
        seen_links.add(link_key)

        deadline = ""
        cal = wrap[0].css("[class*='calendarDate']")
        if cal:
            raw_dl = clean_text(cal[0].get_all_text(" "))
            raw_dl = re.sub(r"^deadline\s*", "", raw_dl, flags=re.I)
            deadline = parse_deadline(raw_dl)

        award = ""
        eligibility = ""
        for block in wrap[0].css("[class*='awardCont']"):
            head_els = block.css("h4")
            head = clean_text(head_els[0].get_all_text(" ")) if head_els else ""
            val = re.sub(r"\s+", " ", (block.get_all_text(" ") or "")).strip()
            val = re.sub(r"^.*?Award\s*(.*)$", r"\1", val, flags=re.I)
            val = re.sub(r"^.*?Eligibility\s*(.*)$", r"\1", val, flags=re.I)
            val = val[:300]
            if "award" in head.lower() and not award:
                award = val
            elif "eligibility" in head.lower() and not eligibility:
                eligibility = val

        notes_parts = ["Scholarship for Indian students. Source: Buddy4Study."]
        if award:
            notes_parts.append(f"Award: {award}.")
        if eligibility:
            notes_parts.append(f"Eligibility: {eligibility}.")

        tags = ["india", "scholarship", "education"]
        if award:
            tags.append("funding")

        item = ScrapeItem(
            title=title,
            type="Certification",
            source="Buddy4Study",
            link=link,
            deadline=deadline,
            eligibility=eligibility or "Indian students",
            tags=tags,
            location="India",
            organizer="",
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)
            logger.info("  Found: %s | %s", title[:50], deadline)

    items = deduplicate_by_link(items)
    logger.info("Buddy4Study: scraped %d scholarships", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_buddy4study()
    print(f"Buddy4Study: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")