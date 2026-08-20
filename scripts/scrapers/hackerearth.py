"""
HackerEarth challenges scraper — ENHANCED.
Tier-2 detail page scraping for deadline, prize, tags, eligibility.
"""

from __future__ import annotations

import re
import json
import logging
import time
from datetime import datetime
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
    for el in card.css("span") + card.css("div"):
        text = clean_text(el.text)
        cls = el.attrib.get("class", "") if hasattr(el, "attrib") else ""
        if text and len(text) < 30 and len(text) > 1:
            if any(kw in cls.lower() for kw in ["badge", "tag", "chip", "label", "pill"]):
                tags.append(text)
            elif any(kw in text.lower() for kw in ["ai", "ml", "blockchain", "web", "mobile", "data", "cloud", "cybersecurity", "iot", "fintech", "health", "education", "sustainability", "open innovation", "beginner", "intermediate", "advanced"]):
                tags.append(text)
    return list(set(tags))[:5]


def _extract_detail_data(page, url: str) -> dict:
    """Extract rich data from a HackerEarth detail page."""
    updates = {}
    try:
        body = str(page.body) if page.body else ""
        body_text = re.sub(r'<[^>]+>', ' ', body)
        body_text = re.sub(r'\s+', ' ', body_text).strip()
        body_lower = body_text.lower()

        # Meta tags
        og_title = page.css('meta[property="og:title"]')
        og_desc = page.css('meta[property="og:description"]')

        # Title from og:title (more reliable)
        if og_title:
            title = clean_text(og_title[0].attrib.get("content", ""))
            if title:
                updates["title"] = title.split("|")[0].strip()

        # Description
        description = ""
        if og_desc:
            description = clean_text(og_desc[0].attrib.get("content", ""))
        if not description:
            meta_desc = page.css('meta[name="description"]')
            if meta_desc:
                description = clean_text(meta_desc[0].attrib.get("content", ""))
        if description:
            updates["description"] = description

        # Deadline from body text
        date_patterns = [
            r'(?:deadline|last\s+date|registrations?\s+(?:close|end))[:\s]*(\w+\s+\d{1,2},?\s*\d{4})',
            r'(?:deadline|last\s+date)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:end(?:ing)?\s+date)[:\s]*(\w+\s+\d{1,2},?\s*\d{4})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, body_lower)
            if match:
                parsed = parse_deadline(match.group(1))
                if parsed:
                    updates["deadline"] = parsed
                    break

        # Prize from body text
        prize_patterns = [
            r'(?:prize|reward|worth)[:\s]*(?:total\s+)?(?:inr|₹|usd|\$)\s*([\d,]+)',
            r'(?:₹|inr)\s*([\d,]+)\s*(?:in\s+prizes?|total|worth)',
            r'(?:prize|worth)\s+(?:of\s+)?(?:₹|inr|usd|\$)\s*([\d,]+)',
        ]
        for pattern in prize_patterns:
            match = re.search(pattern, body_lower)
            if match:
                amount = match.group(1).replace(",", "")
                if int(amount) > 0:
                    symbol = "\u20b9" if "inr" in pattern or "₹" in pattern else "$"
                    updates["prize_pool"] = f"{symbol}{int(amount):,}"
                    break

        # Tags from body text
        tag_keywords = [
            "artificial intelligence", "machine learning", "blockchain", "web development",
            "mobile", "data science", "cloud", "cybersecurity", "iot", "fintech",
            "health", "education", "sustainability", "open innovation", "nlp",
            "computer vision", "deep learning", "python", "javascript"
        ]
        tags = []
        for kw in tag_keywords:
            if kw in body_lower:
                tags.append(kw.title())
        if tags:
            updates["tags"] = tags[:5]

        # Eligibility from body
        elig_parts = []
        if "student" in body_lower:
            elig_parts.append("Students")
        if "open to all" in body_lower or "everyone" in body_lower:
            elig_parts.append("Open to all")
        if "developer" in body_lower:
            elig_parts.append("Developers")
        if "beginner" in body_lower:
            elig_parts.append("Beginners welcome")
        if "professional" in body_lower:
            elig_parts.append("Professionals")
        if elig_parts:
            updates["eligibility"] = ", ".join(elig_parts)

        # Participants from body
        part_match = re.search(r'(\d+)\s*(?:\+?\s*)?(?:participants?|developers?|submissions?)', body_lower)
        if part_match:
            updates["participants"] = part_match.group(1)

        # Location
        if "online" in body_lower:
            updates["location"] = "Online"
        elif "offline" in body_lower or "onsite" in body_lower or "in-person" in body_lower:
            updates["location"] = "Offline"
        elif "hybrid" in body_lower:
            updates["location"] = "Hybrid"

        # Organizer from meta or body
        author = page.css('meta[name="author"]')
        if author:
            org = clean_text(author[0].attrib.get("content", ""))
            if org and org.lower() not in ("hackerearth", ""):
                updates["organizer"] = org

    except Exception as e:
        logger.debug(f"  Detail extraction error for {url}: {e}")
    return updates


def scrape_hackerearth() -> list[ScrapeItem]:
    """Scrape challenges from HackerEarth with Tier-2 detail enrichment."""
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

            _CARD_SELECTOR = "div.group.relative.w-full.block"
            cards = list(page.css(_CARD_SELECTOR))
            seen_card_hrefs: set[str] = set()
            for c in cards:
                h = _extract_challenge_link(c)
                if h:
                    seen_card_hrefs.add(h)

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

            if len(cards) < 5:
                for link_el in page.css('a[href*="/challenges/"]'):
                    href = link_el.attrib.get("href", "")
                    if not href or href in seen_card_hrefs:
                        continue
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
                title_el = card.css("h3")
                title = clean_text(title_el[0].text if title_el else "")
                if not title or len(title) < 3 or title in seen_titles:
                    continue
                seen_titles.add(title)

                href = _extract_challenge_link(card)
                link = (
                    href if href.startswith("http")
                    else f"https://www.hackerearth.com{href}" if href else ""
                )
                if not link:
                    continue

                status = ""
                for sp in card.css("div.inline-flex span"):
                    st = clean_text(sp.text)
                    if st and st not in ("", "•") and "pulse" not in st.lower():
                        status = st
                        break

                participants = ""
                for pel in card.css("div.flex.items-center span"):
                    pt = clean_text(pel.text)
                    if pt and (
                        pt.replace(".", "").replace("K", "").replace(",", "").strip().isdigit()
                        or "k" in pt.lower()
                    ):
                        participants = pt
                        break

                company_el = card.css("div.text-muted-foreground")
                company = clean_text(company_el[0].text if company_el else "")

                tags = _extract_tags_from_card(card)

                notes_parts = ["Source: HackerEarth."]
                if company:
                    notes_parts.append(f"Company: {company}.")
                if status:
                    notes_parts.append(f"Status: {status}.")
                if participants:
                    notes_parts.append(f"Participants: {participants}.")

                item = ScrapeItem(
                    title=title,
                    type="Hackathon",
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

    # Tier-2: Visit ALL detail pages for deadline, prize, tags, eligibility
    logger.info(f"Running Tier-2 detail enrichment for all {len(items)} HackerEarth items...")
    for i, item in enumerate(items):
        if i > 0:
            time.sleep(REQUEST_DELAY)
        logger.info(f"  [{i+1}/{len(items)}] Enriching: {item.title}")
        try:
            page = StealthyFetcher.fetch(
                item.link,
                headless=True,
                disable_resources=True,
                network_idle=True,
                timeout=20000,
            )
            if page.status == 200:
                detail = _extract_detail_data(page, item.link)
                if detail.get("deadline") and not item.deadline:
                    item.deadline = detail["deadline"]
                if detail.get("prize_pool") and not item.prize_pool:
                    item.prize_pool = detail["prize_pool"]
                if detail.get("tags") and not item.tags:
                    item.tags = detail["tags"]
                if detail.get("eligibility") and item.eligibility == "Open to all developers":
                    item.eligibility = detail["eligibility"]
                if detail.get("participants") and not item.participants:
                    item.participants = detail["participants"]
                if detail.get("organizer") and not item.organizer:
                    item.organizer = detail["organizer"]
                if detail.get("location"):
                    item.location = detail["location"]
                if detail.get("description"):
                    item.notes = f"{item.notes} {detail['description'][:200]}".strip()
                logger.info(f"    -> deadline={item.deadline} prize={item.prize_pool} tags={item.tags}")
        except Exception as e:
            logger.debug(f"    Enrichment error: {e}")

    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackerearth()
    print(f"\nTotal: {len(results)} challenges\n")
    for item in results:
        print(f"  {item.title} | deadline={item.deadline or '(no deadline)'} | prize={item.prize_pool} | tags={item.tags} | {item.link}")
