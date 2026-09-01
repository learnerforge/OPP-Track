"""
Challenge.gov scraper (via USA.gov successor).

Challenge.gov was sunset on March 30, 2026. Active federal challenges
now live on USA.gov at /find-active-challenge. This scraper fetches
the listing page, then visits each challenge detail page to extract
structured data (agency, deadline, prizes) from the info tables.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link, parse_deadline

logger = logging.getLogger(__name__)

LISTING_URL = "https://www.usa.gov/find-active-challenge"
BASE_URL = "https://www.usa.gov"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _fetch_page(url: str) -> str | None:
    """Fetch a page and return its HTML text, or None on failure."""
    try:
        resp = httpx.get(url, timeout=30, follow_redirects=True, headers={"User-Agent": UA})
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
    return None


def _parse_detail_page(html: str, url: str) -> dict:
    """Extract structured data from a challenge detail page.

    Each detail page has a <table class="table usa-table"> with rows like:
      Sponsoring agency | Administration for Community Living (ACL)
      Start date        | 2/6/2026 9:17 AM ET
      End date          | 2/6/2029 5:00 PM ET
      Prizes            | Total cash prizes: $2,500,000
    """
    from scrapling import Selector
    page = Selector(html, url=url)

    data: dict = {}
    rows = page.css("table.usa-table tr")
    for row in rows:
        th = row.css("th")
        td = row.css("td")
        if th and td:
            key = clean_text(th[0].text).lower()
            val = clean_text(td[0].text)
            if "agency" in key:
                data["agency"] = val
            elif "end date" in key or "deadline" in key:
                data["end_date"] = val
            elif "start date" in key:
                data["start_date"] = val
            elif "prize" in key:
                data["prizes"] = val
            elif "type" in key:
                data["challenge_type"] = val

    # Try to find the external application link
    apply_btn = page.css("a.usa-button")
    if apply_btn:
        href = apply_btn[0].attrib.get("href", "")
        if href and href.startswith("http"):
            data["external_url"] = href

    return data


def scrape_challenge_gov() -> list[ScrapeItem]:
    """Scrape active federal challenges from USA.gov (successor to Challenge.gov).

    Fetches the listing page for challenge cards, then visits each detail
    page to extract agency, deadline, prizes, and application links.
    """
    items: list[ScrapeItem] = []
    logger.info("Fetching USA.gov active challenges: %s", LISTING_URL)

    html = _fetch_page(LISTING_URL)
    if not html:
        logger.error("Failed to fetch USA.gov challenge listing")
        return items

    from scrapling import Selector
    page = Selector(html, url=LISTING_URL)

    # Extract challenge cards from the listing
    cards = page.css("a.usa-card__container.usagov-card")
    if not cards:
        # Fallback: try any card link
        cards = page.css("li.usa-card a[href*='/challenges/']")

    logger.info("Found %d challenge cards on listing page", len(cards))

    for card in cards:
        href = card.attrib.get("href", "")
        if not href:
            continue

        title_el = card.css("h2.usa-card__heading")
        if not title_el:
            continue
        title = clean_text(title_el[0].text)
        if not title:
            continue

        desc_el = card.css("p")
        description = clean_text(desc_el[0].text) if desc_el else ""

        full_url = href if href.startswith("http") else f"{BASE_URL}{href}"

        # Fetch detail page for structured data
        detail = {}
        detail_html = _fetch_page(full_url)
        if detail_html:
            detail = _parse_detail_page(detail_html, full_url)

        agency = detail.get("agency", "")
        end_date_raw = detail.get("end_date", "")
        # USA.gov dates look like "2/6/2029 5:00 PM ET" (US format, M/D/YYYY).
        # "parse_deadline" tries %d/%m/%Y before %m/%d/%Y, which would swap
        # day/month for these US dates, so normalize to ISO YYYY-MM-DD here.
        deadline = ""
        date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', end_date_raw)
        if date_match:
            m, d, y = date_match.groups()
            try:
                deadline = f"{y}-{int(m):02d}-{int(d):02d}"
            except ValueError:
                deadline = ""
        if not deadline:
            deadline = parse_deadline(end_date_raw)
        prizes = detail.get("prizes", "")
        external_url = detail.get("external_url", "")
        link = external_url if external_url else full_url

        tags = ["challenge", "prize", "government", "usa"]
        if agency:
            # Add a short agency tag
            agency_short = agency.split("(")[0].strip().lower()
            agency_tag = re.sub(r'[^a-z0-9]+', '_', agency_short).strip("_")
            if agency_tag:
                tags.append(agency_tag)

        notes_parts = []
        if agency:
            notes_parts.append(f"Agency: {agency}")
        if prizes:
            notes_parts.append(f"Prizes: {prizes}")
        notes_parts.append("Source: USA.gov (formerly challenge.gov)")
        notes = ". ".join(notes_parts)

        item = ScrapeItem(
            title=f"[Challenge.gov] {title}",
            type="Competition",
            source="Challenge.gov",
            link=link,
            deadline=deadline,
            eligibility="Open to US participants (varies by challenge)",
            tags=tags,
            location="Online",
            organizer=agency,
            prize_pool=prizes,
            notes=notes,
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Challenge.gov (via USA.gov): scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_challenge_gov()
    print(f"Challenge.gov: {len(results)} items")
    for item in results[:5]:
        print(f"  {item.title[:60]} | deadline={item.deadline} | {item.organizer}")
