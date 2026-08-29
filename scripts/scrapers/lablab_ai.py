"""
lablab.ai scraper (StealthyFetcher).
hosts AI/ML focused hackathons. The listing lives at /ai-hackathons
(the /events and /hackathons URLs both redirect to a 404 page).
The site is a Next.js app behind Cloudflare — plain httpx gets a 403,
so this scraper uses scrapling's StealthyFetcher (headless Chromium).

Card structure (div.card-animation.card-border.card-shadow):
  - title:   <h2>
  - link:    <a href="/ai-hackathons/<slug>">
  - dates:   <time datetime="..."> around a "SEP 1 - 30" badge + a
             description line like "Dates: Sep 1–30, 2026" (end date
             = hackathon deadline)
  - status:  top-left badge text ("LIVE" / "Register" / "TBA" / "Finished")
  - location: badge + description emojis (Online / Hybrid / On-site)
  - participants: <p class="...text-gray-800..."> count next to the users icon
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import (
    ScrapeItem,
    parse_deadline,
    clean_text,
    deduplicate_by_link,
    classify_location,
)

logger = logging.getLogger(__name__)

LABLAB_URL = "https://lablab.ai/ai-hackathons"
LABLAB_BASE = "https://lablab.ai"

# "Sep 1–30, 2026" / "September 25–27, 2026" -> month, start-day, end-day, year
_DATE_RANGE_MDY = re.compile(
    r"([A-Za-z]{3,9})\s+(\d{1,2})\s*(?:–|-|to)\s*(\d{1,2}),?\s+(\d{4})", re.I
)
# "28 August – 4 September 2026" -> start-day, start-month, end-day, end-month, year
_DATE_RANGE_DMY = re.compile(
    r"(\d{1,2})\s+([A-Za-z]{3,9})\s*(?:–|-|to)\s*(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{4})",
    re.I,
)
# "12-17 October 2026" -> start-day, end-day, month, year
_DATE_RANGE_DD = re.compile(
    r"(\d{1,2})\s*(?:–|-|to)\s*(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})", re.I
)
# Card date badge: "SEP 10 - 17", "SEP 1 - DEC 1", "AUG 28 - SEP 4"
_BADGE_RANGE = re.compile(
    r"([A-Za-z]{3})\s+(\d{1,2})\s*[-–]\s*([A-Za-z]{3}\s+)?(\d{1,2})", re.I
)

PRIZE_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?(?:k|K)?(?:\+)?", re.I)
PARTICIPANT_RE = re.compile(r"^\d+([.,]\d+)?$")

MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        1,
    )
}
MIN_YEAR, MAX_YEAR = 2024, 2037

TAGS_RE = {
    "llm": re.compile(r"\b(llm|gpt|foundation model)\b", re.I),
    "ai agents": re.compile(r"\bagents?\b", re.I),
    "nlp": re.compile(r"\b(nlp|natural language|language model|mistral)\b", re.I),
    "computer vision": re.compile(r"\b(vision|image|video)\b", re.I),
    "voice": re.compile(r"\b(voice|speech|audio)\b", re.I),
    "developer tools": re.compile(r"\b(developer|dev tool|api)\b", re.I),
    "cloud": re.compile(r"\b(cloud|infra|infrastructure)\b", re.I),
    "trading": re.compile(r"\b(trading|fintech|finance|quant)\b", re.I),
}


def _plausible_year(year: str) -> bool:
    """Guard against date-badge numbers (e.g. participant counts) being read as years."""
    try:
        return MIN_YEAR <= int(year) <= MAX_YEAR
    except ValueError:
        return False


def _parse_described_deadline(desc: str) -> str:
    """Extract the end date from '"Dates: Sep 1–30, 2026"' style description text."""
    if not desc:
        return ""
    for pattern in (_DATE_RANGE_DMY, _DATE_RANGE_MDY, _DATE_RANGE_DD):
        for m in pattern.finditer(desc):
            if pattern is _DATE_RANGE_DMY:
                candidate = f"{m.group(3)} {m.group(4)} {m.group(5)}"
            elif pattern is _DATE_RANGE_MDY:
                candidate = f"{m.group(1)} {m.group(3)}, {m.group(4)}"
            else:
                candidate = f"{m.group(2)} {m.group(3)} {m.group(4)}"
            deadline = parse_deadline(candidate)
            if deadline and _plausible_year(deadline[:4]):
                return deadline
    return ""


def _parse_badge_deadline(time_dt: str, badge_text: str) -> str:
    """Compute the end date from the card's <time datetime> + 'SEP 10 - 17' badge."""
    if not badge_text:
        return ""
    m = _BADGE_RANGE.search(badge_text)
    if not m:
        return ""
    end_day = m.group(4)
    end_month_name = m.group(3) or m.group(1)
    end_month = MONTHS.get(end_month_name.strip().lower()[:3])
    if not end_day or not end_month:
        return ""
    if time_dt:
        try:
            start = datetime.fromisoformat(time_dt.replace("Z", "+00:00"))
        except ValueError:
            return ""
        start_year = start.year
        start_month = start.month
    else:
        return ""
    year = start_year
    if end_month < start_month:
        year += 1
    return parse_deadline(f"{int(end_day)} {end_month_name.strip()} {year}")


def _parse_deadline(desc: str, time_dt: str, badge_text: str) -> str:
    """Deadline for the hackathon = end date of the listed build window."""
    deadline = _parse_described_deadline(desc)
    if deadline:
        return deadline
    return _parse_badge_deadline(time_dt, badge_text)


def _parse_card(card) -> ScrapeItem | None:
    """Parse one lablab.ai hackathon card into a ScrapeItem."""
    link_els = card.css("a[href*='/ai-hackathons/']")
    if not link_els:
        return None
    href = link_els[0].attrib.get("href", "")
    if not href:
        return None
    link = urljoin(LABLAB_BASE + "/", href)

    title_els = card.css("h2")
    title = clean_text(title_els[0].text) if title_els else ""
    if not title or len(title) < 3:
        return None

    card_text = clean_text(card.get_all_text())
    if "finished" in card_text.lower():
        logger.info(f"  Skipping finished event: {title}")
        return None

    desc = ""
    for p in card.css("p"):
        pt = clean_text(p.text)
        if len(pt) > 40:
            desc = pt
            break

    time_el = card.css("time")
    time_dt = ""
    badge_text = ""
    if time_el:
        time_dt = time_el[0].attrib.get("datetime", "")
        badge_text = clean_text(time_el[0].text)

    deadline = _parse_deadline(desc, time_dt, badge_text)

    participants = ""
    for p in card.css("p"):
        pt = clean_text(p.text)
        if PARTICIPANT_RE.match(pt):
            participants = pt
            break

    prizes = []
    for pm in PRIZE_RE.findall(desc or card_text):
        if pm not in prizes:
            prizes.append(pm)
    prize_pool = " | ".join(prizes)

    status = ""
    for span in card.css("span"):
        st = clean_text(span.text)
        if st.lower() in ("live", "register", "tba", "finished", "open", "upcoming"):
            status = st
            break

    tags = ["ai", "machine learning", "hackathon"]
    title_desc = f"{title} {card_text}"
    for tag, pattern in TAGS_RE.items():
        if pattern.search(title_desc) and tag not in tags:
            tags.append(tag)

    notes_parts = ["Source: lablab.ai."]
    if status:
        notes_parts.append(f"Status: {status}.")
    if deadline:
        notes_parts.append(f"Build window ends: {deadline}.")

    return ScrapeItem(
        title=title,
        type="Hackathon",
        source="lablab.ai",
        link=link,
        deadline=deadline,
        eligibility="Open to all — AI/tech professionals and domain experts worldwide",
        tags=tags,
        notes=" ".join(notes_parts),
        location=classify_location(card_text),
        prize_pool=prize_pool,
        participants=participants,
        organizer="lablab.ai",
    )


def scrape_lablab_ai() -> list[ScrapeItem]:
    """Scrape upcoming/active AI hackathons from lablab.ai."""
    logger.info("Fetching lablab.ai: %s", LABLAB_URL)
    items: list[ScrapeItem] = []

    try:
        page = StealthyFetcher.fetch(
            LABLAB_URL,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=60000,
        )
    except Exception as e:
        logger.error("lablab.ai fetch failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("lablab.ai returned status %s", page.status)
        return items

    body = getattr(page, "body", None)
    if not body:
        logger.error("lablab.ai returned empty body")
        return items
    html = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)

    from scrapling import Selector

    page_sel = Selector(html, url=LABLAB_URL)

    cards = page_sel.css("div.card-animation.card-border.card-shadow")
    if not cards:
        logger.warning("lablab.ai: no hackathon cards matched")
        return items

    for card in cards:
        try:
            item = _parse_card(card)
        except Exception as e:
            logger.debug(f"  lablab.ai card parse error: {e}")
            continue
        if not item:
            continue
        errors = item.validate()
        if errors:
            logger.debug(f"  Skipping invalid item {item.title}: {errors}")
            continue
        items.append(item)
        logger.info(
            f"  Found: {item.title} | {item.deadline or 'TBA'} | "
            f"{item.location} | {item.prize_pool or '-'} | {item.link}"
        )

    items = deduplicate_by_link(items)
    logger.info("lablab.ai: scraped %d hackathons", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_lablab_ai()
    print(f"lablab.ai: {len(results)} items")
    for item in results:
        print(
            f"  {item.title} | {item.deadline or 'TBA'} | {item.location} | "
            f"prize={item.prize_pool or '-'} | {item.link}"
        )