"""
Unstop hackathon and internship scraper.
Uses StealthyFetcher — Unstop is a JS-rendered Angular SPA.
"""

from __future__ import annotations

import re
import logging
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

UNSTOP_URLS = [
    ("https://unstop.com/competitions?oppstatus=open&usertype=students&domain=2", "Hackathon"),
    ("https://unstop.com/hackathons", "Hackathon"),
]


def _extract_deadline_from_days_left(days_text: str) -> str:
    """Parse '5 days left' into an approximate YYYY-MM-DD date."""
    match = re.search(r'(\d+)\s+days?\s+left', days_text.lower())
    if match:
        from datetime import datetime, timedelta
        days = int(match.group(1))
        target = datetime.now() + timedelta(days=days)
        return target.strftime("%Y-%m-%d")
    return ""


def _extract_deadline_from_text(text: str) -> str:
    """Extract deadline from text like 'Posted Aug 19, 2026' or '5 days left'."""
    if not text:
        return ""
    text_lower = text.lower()
    if any(w in text_lower for w in ("ended", "past", "closed")):
        return ""
    if "days left" in text_lower or "day left" in text_lower:
        return _extract_deadline_from_days_left(text)
    return parse_deadline(text)


def _determine_type(title: str, hint: str) -> str:
    title_lower = title.lower()
    if "intern" in title_lower or "internship" in title_lower:
        return "Internship"
    if "certif" in title_lower:
        return "Certification"
    return hint


def scrape_unstop() -> list[ScrapeItem]:
    """Scrape competitions from Unstop using accurate DOM selectors."""
    items: list[ScrapeItem] = []

    for url, hint_type in UNSTOP_URLS:
        logger.info(f"Fetching Unstop: {url}")
        try:
            page = StealthyFetcher.fetch(
                url,
                headless=True,
                disable_resources=True,
                network_idle=True,
                timeout=30000,
            )

            if page.status != 200:
                logger.warning(f"Unstop returned status {page.status} for {url}")
                continue

            # Unstop competition cards use <a class="item opp_{ID}">
            cards = page.css('a[class*="opp_"]')
            if not cards:
                # Fallback selectors
                cards = (
                    page.css('a[class*="item"]') or
                    page.css('[class*="card"]')
                )

            seen_titles: set[str] = set()
            for card in cards:
                # Title: <h3 itemprop="name" class="double-wrap">
                title_el = card.css('h3[itemprop="name"]') or card.css('h3.double-wrap') or card.css('h3')
                title = clean_text(title_el[0].text if title_el else "")
                if not title or len(title) < 3 or title in seen_titles:
                    continue
                seen_titles.add(title)

                # Link: href on the <a> tag
                href = card.attrib.get("href", "")
                link = href if href.startswith("http") else f"https://unstop.com{href}" if href else ""

                # Organization: <p class="single-wrap">
                org_el = card.css("p.single-wrap")
                org = clean_text(org_el[0].text if org_el else "")

                # Deadline: <div class="dates-fields"> <label class="tag-text">
                dates_div = card.css("div.dates-fields")
                deadline = ""
                posted_date = ""
                if dates_div:
                    date_labels = dates_div[0].css("label.tag-text")
                    for dl in date_labels:
                        dt_text = clean_text(dl.text)
                        if "left" in dt_text.lower() or "day" in dt_text.lower():
                            deadline = _extract_deadline_from_days_left(dt_text)
                        elif "posted" in dt_text.lower():
                            posted_date = dt_text
                        elif not deadline:
                            deadline = _extract_deadline_from_text(dt_text)

                # Tags: <span class="chip_text">
                tag_els = card.css("span.chip_text")
                tags = [clean_text(t.text) for t in tag_els if clean_text(t.text)]

                # Location: <span class="location_text">
                loc_el = card.css("span.location_text")
                location = clean_text(loc_el[0].text if loc_el else "")

                opp_type = _determine_type(title, hint_type)

                notes_parts = ["Source: Unstop."]
                if org:
                    notes_parts.append(f"Org: {org}.")
                if location:
                    notes_parts.append(f"Location: {location}.")

                item = ScrapeItem(
                    title=title,
                    type=opp_type,
                    source="Unstop",
                    link=link or f"https://unstop.com/search?q={title.replace(' ', '+')}",
                    deadline=deadline,
                    eligibility="Check Unstop for eligibility details",
                    tags=tags,
                    notes=" ".join(notes_parts),
                )
                items.append(item)
                logger.info(f"  Found: {title} | {opp_type} | {deadline}")

        except Exception as e:
            logger.error(f"Error scraping Unstop {url}: {e}")

    logger.info(f"Unstop: scraped {len(items)} opportunities")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_unstop()
    for item in results:
        print(f"  {item.title} | {item.type} | {item.deadline} | {item.link}")
