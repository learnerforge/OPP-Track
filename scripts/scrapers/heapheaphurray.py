"""
Heap Heap Hurray scraper.
Scrapes tech events in India from https://events.heapheaphurray.com/.

The site is a Next.js app that publishes schema.org structured data: every
listing page embeds a JSON-LD ``ItemList`` whose entries are full ``Event``
objects (name, startDate, endDate, url, location, keywords,
eventAttendanceMode). That is a stable, official contract, so no browser and
no CSS selectors are required — plain HTTP is enough and a full run takes
seconds. Mirrors the approach already used by reskilll.py.

The homepage exposes only the 20 soonest events, but the site also carries
category and city routes (/hackathons, /meetups, /workshops, /online,
/bengaluru, /ai-events, ...). Each of those has its own JSON-LD ItemList, and
only unioning them all yields the complete catalogue (~320 events). We
therefore crawl every route and deduplicate by event URL.
"""

from __future__ import annotations

import json
import os
import re
import logging
from datetime import datetime, date

import httpx

from scripts.scrapers.base import (
    ScrapeItem,
    clean_text,
    deduplicate_by_link,
    normalize_link,
)

logger = logging.getLogger(__name__)

HEAPHEAPHURRAY_BASE = "https://events.heapheaphurray.com"

# Every listing route on the site — the homepage plus the category and city
# pages. Each renders its own JSON-LD ItemList; only their union is complete.
HEAPHEAPHURRAY_ROUTES = [
    "/",
    # Category routes
    "/hackathons",
    "/meetups",
    "/conferences",
    "/workshops",
    "/online",
    "/ai-events",
    "/cloud-devops-events",
    "/cybersecurity-events",
    "/data-science-events",
    "/genai-events",
    "/hardware-iot-events",
    "/open-source-events",
    "/startup-events",
    "/student-tech-events",
    "/web3-events",
    # City routes
    "/bengaluru",
    "/delhi",
    "/mumbai",
    "/pune",
    "/hyderabad",
    "/chennai",
    "/kolkata",
    "/noida",
    "/gurugram",
    "/kochi",
    "/jaipur",
    "/ahmedabad",
    "/indore",
    "/kozhikode",
    "/lucknow",
    "/nagpur",
    "/coimbatore",
    "/chandigarh",
    "/bhopal",
    "/goa",
    "/dehradun",
    "/ghaziabad",
    "/kanpur",
]

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

LD_JSON_RE = re.compile(
    r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL
)

# The site's own event-type label is recovered from the title and keywords (the
# JSON-LD payload carries only an attendance mode). It is recorded as a tag;
# only the Hackathon case is allowed to influence the canonical type.
_HACK_RE = re.compile(r"\bhack(s|athon|fest|day)?\b", re.I)

DEFAULT_ELIGIBILITY = "Open to developers, students and builders in India; see listing for details"

# Words dropped before comparing titles across sources, so that
# "Build with Ai: ABC (Anybody Can Code)" and "Build with AI - ABC (Anybody Can
# Code)" collapse to the same key.
_TITLE_NOISE_RE = re.compile(
    r"\b(the|a|an|by|at|of|for|and|with|on|in|x|edition|presented)\b"
)


def _parse_iso_date(iso: str) -> str:
    """Convert an ISO-8601 timestamp like '2026-10-18T00:00:00+05:30' to YYYY-MM-DD."""
    if not iso:
        return ""
    text = str(iso).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _title_key(title: str) -> str:
    """Normalise a title so the same opportunity matches across sources.

    Strips source prefixes like '[Reskilll]', punctuation, accents and common
    filler words. Only used for replica detection — never for output.
    """
    if not title:
        return ""
    key = title.lower()
    key = re.sub(r"\[[^\]]*\]", " ", key)
    key = re.sub(r"[^a-z0-9 ]+", " ", key)
    key = _TITLE_NOISE_RE.sub(" ", key)
    return re.sub(r"\s+", " ", key).strip()


def _extract_item_list(html: str) -> list[dict]:
    """Pull the Event objects out of the page's JSON-LD ItemList block(s)."""
    events: list[dict] = []
    for raw in LD_JSON_RE.findall(html):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or obj.get("@type") != "ItemList":
            continue
        for entry in obj.get("itemListElement") or []:
            if not isinstance(entry, dict):
                continue
            event = entry.get("item")
            if isinstance(event, dict) and event.get("name"):
                events.append(event)
    return events


def _attendance_mode(event: dict) -> str:
    """Map schema.org eventAttendanceMode onto Online / Hybrid / Offline."""
    mode = str(event.get("eventAttendanceMode") or "").lower()
    if "mixed" in mode or "hybrid" in mode:
        return "Hybrid"
    if "online" in mode:
        return "Online"
    if "offline" in mode:
        return "Offline"
    return ""


def _location_details(event: dict) -> str:
    """Build 'City, Country' from the schema.org Place/location field."""
    loc = event.get("location")
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    if not isinstance(loc, dict):
        return ""
    address = loc.get("address")
    if isinstance(address, list):
        address = address[0] if address else {}
    if not isinstance(address, dict):
        address = {}
    city = clean_text(address.get("addressLocality") or loc.get("name") or "")
    country = clean_text(address.get("addressCountry") or "")
    return ", ".join(p for p in (city, country) if p)


def _extract_tags(event: dict) -> list[str]:
    """Site tag plus the event's keyword list, normalised and deduplicated."""
    raw = event.get("keywords")
    if isinstance(raw, list):
        parts = [clean_text(k) for k in raw]
    else:
        parts = [clean_text(k) for k in str(raw or "").split(",")]

    tags = ["heapheap hurray", "india"]
    seen = {t.lower() for t in tags}
    for p in parts:
        if p and p.lower() not in seen:
            seen.add(p.lower())
            tags.append(p)
    return tags


def _is_hackathon(title: str, tags: list[str]) -> bool:
    """True when the listing is clearly a hackathon.

    Matches the ``hack`` stem at a word boundary so real-world names like
    'T HACKS 9.0', 'Hack On Hills' and 'Hefty-Hacks' are caught, while one-word
    names that merely embed the stem ('Hacktoberfest Meetup') are not.
    """
    return bool(_HACK_RE.search(f"{title} {' '.join(tags)}"))


def _map_event(event: dict) -> ScrapeItem | None:
    """Map a single schema.org Event dict to a ScrapeItem."""
    title = clean_text(event.get("name"))
    link = clean_text(event.get("url"))
    if not title or not link.startswith(("http://", "https://")):
        return None

    start = _parse_iso_date(event.get("startDate"))
    end = _parse_iso_date(event.get("endDate"))
    # The dataset's `deadline` is a YYYY-MM-DD date. For an event, the last day
    # it is open is its end date, falling back to the start when end is absent.
    deadline = end or start

    attendance = _attendance_mode(event)
    location_details = _location_details(event)
    tags = _extract_tags(event)

    # Hackathons map directly; conferences, meetups, workshops and webinars have
    # no exact counterpart in the canonical four-value type set, so they share
    # the participatory bucket and keep their real label in tags.
    if _is_hackathon(title, tags):
        opp_type = "Hackathon"
        tags.insert(2, "hackathon")
    else:
        opp_type = "Competition"

    notes_parts = ["Source: events.heapheaphurray.com (tech events in India)."]
    if start and end and start != end:
        notes_parts.append(f"Runs {start} to {end}.")
    elif start:
        notes_parts.append(f"Starts {start}.")
    if location_details:
        notes_parts.append(f"Location: {location_details}.")
    if attendance:
        notes_parts.append(f"{attendance} event.")

    item = ScrapeItem(
        title=title,
        type=opp_type,
        source="Heap Heap Hurray",
        link=link,
        deadline=deadline,
        eligibility=DEFAULT_ELIGIBILITY,
        tags=tags,
        notes=" ".join(notes_parts),
        location=attendance,
        organizer="Heap Heap Hurray",
    )
    errors = item.validate()
    if errors:
        logger.debug(f"  Skipping invalid item {title}: {errors}")
        return None
    return item


def _existing_keys() -> tuple[set[str], set[str]]:
    """Load the link and title keys of everything already in the dataset.

    Heap Heap Hurray is an aggregator — each listing points at the organiser's
    own page, and many of those pages are already scraped first-hand (Unstop,
    MLH, Devfolio, Devpost, HackIndia, ...). Emitting them again would put a
    replica of an existing opportunity into the canonical dataset. Reading the
    current data file lets us skip those regardless of which source owns them,
    instead of hardcoding a list of hosts that would rot.

    Returns (link_keys, title_keys). Missing or unreadable data yields empty
    sets, in which case the guard is simply inactive.
    """
    data_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "scraped_opportunities.json",
    )
    link_keys: set[str] = set()
    title_keys: set[str] = set()
    if not os.path.exists(data_file):
        logger.info("Heap Heap Hurray: no existing dataset, replica guard inactive")
        return link_keys, title_keys

    try:
        with open(data_file, "r", encoding="utf-8") as fh:
            existing = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Heap Heap Hurray: could not read existing dataset ({e}); replica guard inactive")
        return link_keys, title_keys

    for entry in existing:
        if not isinstance(entry, dict):
            continue
        # Our own previous output must not block itself on re-runs.
        if entry.get("source") == "Heap Heap Hurray":
            continue
        link_key = normalize_link(entry.get("link", ""))
        if link_key:
            link_keys.add(link_key)
        title_key = _title_key(entry.get("title", ""))
        if title_key:
            title_keys.add(title_key)
    logger.info(
        f"Heap Heap Hurray: replica guard loaded {len(link_keys)} links / "
        f"{len(title_keys)} titles from the existing dataset"
    )
    return link_keys, title_keys


def _is_replica(item: ScrapeItem, link_keys: set[str], title_keys: set[str]) -> bool:
    """True when the item duplicates an opportunity already in the dataset.

    Link match is the strong signal (same page). Title match catches the cases
    where each source links to its own URL for the same event.
    """
    link_key = normalize_link(item.link)
    if link_key and link_key in link_keys:
        return True
    title_key = _title_key(item.title)
    return bool(title_key) and title_key in title_keys


def scrape_heapheaphurray() -> list[ScrapeItem]:
    """Scrape every tech event listed on events.heapheaphurray.com."""
    items: list[ScrapeItem] = []
    # url -> schema.org Event. Deduplicating on the canonical event URL across
    # all routes is what turns the ~20-per-page listings into the full set.
    seen: dict[str, dict] = {}
    logger.info(f"Fetching Heap Heap Hurray events: {HEAPHEAPHURRAY_BASE}")

    link_keys, title_keys = _existing_keys()

    try:
        with httpx.Client(
            timeout=30, follow_redirects=True, headers={"User-Agent": UA}
        ) as client:
            for route in HEAPHEAPHURRAY_ROUTES:
                url = HEAPHEAPHURRAY_BASE + route
                try:
                    resp = client.get(url)
                except Exception as e:
                    logger.warning(f"  request failed for {url}: {e}")
                    continue
                if resp.status_code != 200:
                    logger.warning(f"Heap Heap Hurray returned {resp.status_code} for {url}")
                    continue

                found = _extract_item_list(resp.text)
                new = 0
                for event in found:
                    key = normalize_link(event.get("url"))
                    if not key or key in seen:
                        continue
                    seen[key] = event
                    new += 1
                logger.info(f"  {route}: {len(found)} events ({new} new)")
    except Exception as e:
        logger.error(f"Heap Heap Hurray request failed: {e}")
        return items

    if not seen:
        logger.warning("Heap Heap Hurray: no events found on any route")
        return items

    today = date.today()
    replicas = 0
    for event in seen.values():
        end = _parse_iso_date(event.get("endDate"))
        start = _parse_iso_date(event.get("startDate"))
        cutoff = end or start
        if cutoff:
            try:
                if datetime.strptime(cutoff, "%Y-%m-%d").date() < today:
                    logger.debug(f"  Skipping ended event: {event.get('name')} ({cutoff})")
                    continue
            except ValueError:
                pass
        item = _map_event(event)
        if not item:
            continue
        if _is_replica(item, link_keys, title_keys):
            replicas += 1
            logger.info(f"  Skipping replica already in dataset: {item.title}")
            continue
        items.append(item)
        logger.info(f"  Found: {item.title} | {item.deadline} | {item.type}")

    items = deduplicate_by_link(items)
    logger.info(
        f"Heap Heap Hurray: scraped {len(items)} events "
        f"({len(seen)} unique across {len(HEAPHEAPHURRAY_ROUTES)} routes, "
        f"{replicas} replicas skipped)"
    )
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_heapheaphurray()
    print(f"Heap Heap Hurray: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.location} | {item.link}")
