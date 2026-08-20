"""
Unstop hackathon and internship scraper — ENHANCED.
Fixes:
  1. Extract real eligibility from tags/chips
  2. Better location extraction
  3. Extract organizer from page
"""

from __future__ import annotations

import re
import logging
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, classify_location

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


def _build_eligibility_from_tags(tags: list[str], title: str) -> str:
    """Build real eligibility text from tags and title."""
    elig_parts = []
    title_lower = title.lower()

    # Check tags for eligibility hints
    for tag in tags:
        tag_lower = tag.lower()
        if any(kw in tag_lower for kw in ["student", "college", "university", "bachelor", "master", "phd"]):
            elig_parts.append("Students")
        elif any(kw in tag_lower for kw in ["professional", "experienced", "working"]):
            elig_parts.append("Professionals")
        elif any(kw in tag_lower for kw in ["beginner", "fresher", "entry"]):
            elig_parts.append("Beginners welcome")
        elif any(kw in tag_lower for kw in ["open", "all", "everyone"]):
            elig_parts.append("Open to all")

    # Check title for hints
    if "student" in title_lower or "college" in title_lower:
        elig_parts.append("Students")
    if "beginner" in title_lower or "fresher" in title_lower:
        elig_parts.append("Beginners welcome")
    if "open" in title_lower:
        elig_parts.append("Open to all")

    if not elig_parts:
        elig_parts.append("Check Unstop for eligibility details")

    return ", ".join(list(set(elig_parts)))


def scrape_unstop() -> list[ScrapeItem]:
    """Scrape competitions from Unstop with enhanced eligibility extraction."""
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
                cards = (
                    page.css('a[class*="item"]') or
                    page.css('[class*="card"]')
                )

            seen_titles: set[str] = set()
            for card in cards:
                # Title
                title_el = card.css('h3[itemprop="name"]') or card.css('h3.double-wrap') or card.css('h3')
                title = clean_text(title_el[0].text if title_el else "")
                if not title or len(title) < 3 or title in seen_titles:
                    continue
                seen_titles.add(title)

                # Link
                href = card.attrib.get("href", "")
                link = href if href.startswith("http") else f"https://unstop.com{href}" if href else ""

                # Organization
                org_el = card.css("p.single-wrap")
                org = clean_text(org_el[0].text if org_el else "")

                # Deadline
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

                # Tags
                tag_els = card.css("span.chip_text")
                tags = [clean_text(t.text) for t in tag_els if clean_text(t.text)]

                # Location
                loc_el = card.css("span.location_text")
                location = clean_text(loc_el[0].text if loc_el else "")

                opp_type = _determine_type(title, hint_type)

                # Build real eligibility from tags
                eligibility = _build_eligibility_from_tags(tags, title)

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
                    eligibility=eligibility,
                    tags=tags,
                    notes=" ".join(notes_parts),
                    location=classify_location(location) if location else "",
                    organizer=org,
                )
                items.append(item)
                logger.info(f"  Found: {title} | {opp_type} | {deadline} | elig={eligibility[:50]}")

        except Exception as e:
            logger.error(f"Error scraping Unstop {url}: {e}")

    logger.info(f"Unstop: scraped {len(items)} opportunities")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_unstop()
    for item in results:
        print(f"  {item.title} | {item.type} | {item.deadline} | {item.eligibility[:60]} | {item.link}")
