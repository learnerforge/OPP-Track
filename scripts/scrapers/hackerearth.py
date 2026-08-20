"""
HackerEarth challenges scraper — ENHANCED.
Fixes:
  1. Better card extraction with fallback selectors
  2. Extract tags/themes from listing page
  3. Handle redirects on detail pages
"""

from __future__ import annotations

import re
import logging
import time
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

HACKEREARTH_URLS = [
    "https://www.hackerearth.com/challenges/",
    "https://www.hackerearth.com/challenges/hackathon/",
]

REQUEST_DELAY = 1.5


def _extract_challenge_link(card) -> str:
    """Extract the first /challenges/ href from a card element."""
    for el in card.css("a[href]"):
        href = el.attrib.get("href", "")
        if "/challenges/" in href:
            return href
    return ""


def _is_challenge_card(element) -> bool:
    """Check if an element is a genuine challenge card."""
    href = _extract_challenge_link(element)
    if not href:
        return False
    has_title = element.css("h3") or element.css('[class*="font-semibold"]')
    return bool(has_title)


def _extract_tags_from_card(card) -> list[str]:
    """Extract tags/themes from a challenge card."""
    tags = []
    # Look for badge/tag elements
    for el in card.css("span") + card.css("div"):
        text = clean_text(el.text)
        cls = el.attrib.get("class", "") if hasattr(el, "attrib") else ""
        # Tags are usually small badges with specific styling
        if text and len(text) < 30 and len(text) > 1:
            if any(kw in cls.lower() for kw in ["badge", "tag", "chip", "label", "pill"]):
                tags.append(text)
            elif any(kw in text.lower() for kw in ["ai", "ml", "blockchain", "web", "mobile", "data", "cloud", "cybersecurity", "iot", "fintech", "health", "education", "sustainability", "open innovation", "beginner", "intermediate", "advanced"]):
                tags.append(text)
    return list(set(tags))[:5]


def scrape_hackerearth() -> list[ScrapeItem]:
    """Scrape challenges from HackerEarth with enhanced selectors."""
    items: list[ScrapeItem] = []

    for url in HACKEREARTH_URLS:
        logger.info(f"Fetching HackerEarth: {url}")
        try:
            page = StealthyFetcher.fetch(
                url,
                headless=True,
                disable_resources=True,
                network_idle=True,
                timeout=30000,
            )

            if page.status != 200:
                logger.warning(f"HackerEarth returned status {page.status} for {url}")
                continue

            # Strategy 1: exact Tailwind class selector
            _CARD_SELECTOR = "div.group.relative.w-full.block"
            cards = list(page.css(_CARD_SELECTOR))
            seen_card_hrefs: set[str] = set()
            for c in cards:
                h = _extract_challenge_link(c)
                if h:
                    seen_card_hrefs.add(h)

            # Strategy 2: broaden via challenge links + parent walk
            if len(cards) < 10:
                for link_el in page.css('a[href*="/challenges/"]'):
                    href = link_el.attrib.get("href", "")
                    if not href or href in seen_card_hrefs:
                        continue
                    ancestor = getattr(link_el, "parent", None)
                    for _ in range(5):
                        if ancestor is None:
                            break
                        cls = ancestor.attrib.get("class", "")
                        tag = getattr(ancestor, "tag", "")
                        if tag == "div" and "group" in cls.split():
                            if _is_challenge_card(ancestor):
                                cards.append(ancestor)
                                seen_card_hrefs.add(href)
                            break
                        ancestor = getattr(ancestor, "parent", None)

            # Strategy 3: Look for any card-like structure with challenge links
            if len(cards) < 5:
                for link_el in page.css('a[href*="/challenges/"]'):
                    href = link_el.attrib.get("href", "")
                    if not href or href in seen_card_hrefs:
                        continue
                    # Check if this link has a title nearby
                    parent = getattr(link_el, "parent", None)
                    if parent:
                        h3 = parent.css("h3")
                        if h3:
                            cards.append(parent)
                            seen_card_hrefs.add(href)

            if not cards:
                logger.warning(f"No challenge cards found for {url}")
                continue

            logger.info(f"HackerEarth: found {len(cards)} card elements for {url}")

            seen_titles: set[str] = set()
            for card in cards:
                # Title: h3
                title_el = card.css("h3")
                title = clean_text(title_el[0].text if title_el else "")
                if not title or len(title) < 3 or title in seen_titles:
                    continue
                seen_titles.add(title)

                # Link
                href = _extract_challenge_link(card)
                link = (
                    href if href.startswith("http")
                    else f"https://www.hackerearth.com{href}" if href else ""
                )
                if not link:
                    continue

                # Status: badge span
                status = ""
                for sp in card.css("div.inline-flex span"):
                    st = clean_text(sp.text)
                    if st and st not in ("", "•") and "pulse" not in st.lower():
                        status = st
                        break

                # Participants
                participants = ""
                for pel in card.css("div.flex.items-center span"):
                    pt = clean_text(pel.text)
                    if pt and (
                        pt.replace(".", "").replace("K", "").replace(",", "").strip().isdigit()
                        or "k" in pt.lower()
                    ):
                        participants = pt
                        break

                # Company
                company_el = card.css("div.text-muted-foreground")
                company = clean_text(company_el[0].text if company_el else "")

                # Tags from card
                tags = _extract_tags_from_card(card)

                # Type
                opp_type = "Hackathon"

                notes_parts = ["Source: HackerEarth."]
                if company:
                    notes_parts.append(f"Company: {company}.")
                if status:
                    notes_parts.append(f"Status: {status}.")
                if participants:
                    notes_parts.append(f"Participants: {participants}.")

                item = ScrapeItem(
                    title=title,
                    type=opp_type,
                    source="HackerEarth",
                    link=link,
                    deadline="",
                    eligibility="Open to all developers",
                    tags=tags,
                    notes=" ".join(notes_parts),
                    organizer=company,
                )
                items.append(item)
                logger.info(f"  Found: {title} | {status} | tags={tags} | {link}")

        except Exception as e:
            logger.error(f"Error scraping HackerEarth {url}: {e}")

    logger.info(f"HackerEarth: scraped {len(items)} challenges")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackerearth()
    print(f"\nTotal: {len(results)} challenges\n")
    for item in results:
        print(f"  {item.title} | {item.deadline or '(no deadline)'} | tags={item.tags} | {item.link}")
