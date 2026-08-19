"""
HackerEarth challenges scraper.
HackerEarth is a Next.js app with SSR — uses StealthyFetcher for reliability.

NOTE: HackerEarth uses virtual scrolling on the challenges listing page.
      Only the above-the-fold cards (typically 3-5) are present in the initial
      server-rendered HTML. The rest load dynamically as the user scrolls.
      StealthyFetcher does not scroll, so we only capture the initially
      visible cards. This is a known limitation of this scraper.
      Deadlines are also not shown on the listing page — only status badges.
"""

from __future__ import annotations

import logging
from scrapling.fetchers import StealthyFetcher
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text

logger = logging.getLogger(__name__)

HACKEREARTH_URLS = [
    "https://www.hackerearth.com/challenges/",
]

# CSS selector for challenge cards: <div class="group relative w-full block">
# This is the exact Tailwind class combination HackerEarth uses for each card wrapper.
_CARD_SELECTOR = "div.group.relative.w-full.block"


def _extract_challenge_link(card) -> str:
    """Extract the first /challenges/ href from a card element."""
    for el in card.css("a[href]"):
        href = el.attrib.get("href", "")
        if "/challenges/" in href:
            return href
    return ""


def _is_challenge_card(element) -> bool:
    """Check if an element is a genuine challenge card by verifying it
    contains both a challenge link and a title element."""
    href = _extract_challenge_link(element)
    if not href:
        return False
    has_title = element.css("h3") or element.css('[class*="font-semibold"]')
    return bool(has_title)


def scrape_hackerearth() -> list[ScrapeItem]:
    """Scrape challenges from HackerEarth."""
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

            # ── Strategy 1: exact Tailwind class selector ──────────────
            # Matches the ~3 above-the-fold cards present in the SSR HTML.
            cards = list(page.css(_CARD_SELECTOR))
            seen_card_hrefs: set[str] = set()
            for c in cards:
                h = _extract_challenge_link(c)
                if h:
                    seen_card_hrefs.add(h)

            # ── Strategy 2: broaden via challenge links + parent walk ───
            # If we got very few results, look for all <a> tags linking to
            # /challenges/ and walk up to the nearest div.group ancestor.
            # This catches cards whose class list was reordered or extended
            # by client-side hydration.
            if len(cards) < 10:
                for link_el in page.css('a[href*="/challenges/"]'):
                    href = link_el.attrib.get("href", "")
                    if not href or href in seen_card_hrefs:
                        continue
                    # Walk up to find the card wrapper (div with "group" class)
                    ancestor = getattr(link_el, "parent", None)
                    for _ in range(5):  # limit depth to avoid climbing too far
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

                # Status: badge span (Live / Registration Open / Upcoming)
                status = ""
                for sp in card.css("div.inline-flex span"):
                    st = clean_text(sp.text)
                    if st and st not in ("", "•") and "pulse" not in st.lower():
                        status = st
                        break

                # Participants: span next to Users SVG
                participants = ""
                for pel in card.css("div.flex.items-center span"):
                    pt = clean_text(pel.text)
                    if pt and (
                        pt.replace(".", "").replace("K", "").replace(",", "").strip().isdigit()
                        or "k" in pt.lower()
                    ):
                        participants = pt
                        break

                # Company: div.text-muted-foreground
                company_el = card.css("div.text-muted-foreground")
                company = clean_text(company_el[0].text if company_el else "")

                # Determine type from URL pattern
                opp_type = "Hackathon"
                if "/competitive/" in href:
                    opp_type = "Hackathon"

                notes_parts = ["Source: HackerEarth."]
                if company:
                    notes_parts.append(f"Company: {company}.")
                if status:
                    notes_parts.append(f"Status: {status}.")
                if participants:
                    notes_parts.append(f"Participants: {participants}.")

                # Deadline is not available on the listing page — only status badges.
                item = ScrapeItem(
                    title=title,
                    type=opp_type,
                    source="HackerEarth",
                    link=link,
                    deadline="",
                    eligibility="Open to all developers",
                    tags=[],
                    notes=" ".join(notes_parts),
                )
                items.append(item)
                logger.info(f"  Found: {title} | {status} | {link}")

        except Exception as e:
            logger.error(f"Error scraping HackerEarth {url}: {e}")

    logger.info(f"HackerEarth: scraped {len(items)} challenges")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackerearth()
    print(f"\nTotal: {len(results)} challenges\n")
    for item in results:
        print(f"  {item.title} | {item.deadline or '(no deadline)'} | {item.link}")
