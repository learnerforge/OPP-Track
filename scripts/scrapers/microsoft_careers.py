"""
Microsoft Careers scraper.
Scrapes Microsoft's public careers sitemap for internship roles.

Microsoft's careers portal (apply.careers.microsoft.com) is an Eightfold.ai
career site. Its public jobs API is WAF-protected/PCSX-restricted, but the
public ``/careers/sitemap.xml`` lists every open role as a canonical job URL
whose slug encodes the real title and location. We parse that sitemap and derive
scrape items for internship roles.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

MS_SITEMAP = "https://apply.careers.microsoft.com/careers/sitemap.xml"
MS_SEARCH = "https://apply.careers.microsoft.com/careers?q=intern"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# phrase tokens to strip from the middle/end of a role slug (not locations)
_NOISE_PHRASES = (
    "opportunities-for-university-students",
    "jobs-for-university-students",
    "for-university-students",
    "opportunities-for-university-grads",
    "campus-recruiting",
    "university-graduates",
    "2027",
    "2026",
)

_LOC_PRIORITY = (
    # high-cardinality real cities/countries seen in Microsoft slugs
    "redmond", "united-states", "atlanta", "bellevue", "bengaluru",
    "cape-town", "chicago", "dublin", "gauteng", "hyderabad", "india",
    "johannesburg", "london", "multiple-locations", "new-york", "redmond",
    "seattle", "singapore", "south-africa", "sydney", "tel-aviv",
    "toronto", "western-cape", "zurich", "warsaw", "austin", "poland",
)

# trailing slug tokens that mark the location part of a job slug
_LOCATION_TOKENS = {
    "united-states", "redmond", "atlanta", "austin", "chicago", "irvine",
    "kirkland", "mountain-view", "new-york", "seattle", "sunnyvale",
    "indianapolis", "multiple-locations", "india", "bengaluru", "hyderabad",
    "south-africa", "cape-town", "johannesburg", "gauteng", "western-cape",
    "canada", "toronto", "vancouver", "uk", "london", "ireland", "dublin",
    "germany", "munich", "berlin", "netherlands", "amsterdam", "switzerland",
    "zurich", "sweden", "stockholm", "israel", "tel-aviv", "japan", "tokyo",
    "osaka", "korea", "seoul", "china", "beijing", "shanghai", "hong-kong",
    "singapore", "australia", "sydney", "melbourne", "new-south-wales",
    "victoria", "pole-positions", "poland", "warsaw", "greece", "athens",
    "france", "paris", "egypt", "cairo", "romania", "bucharest",
    "washington", "california", "texas", "georgia", "massachusetts",
    "colorado", "virginia", "florida", "north-carolina", "oregon",
    "pennsylvania", "new-jersey", "arizona", "taiwan", "taipei",
    "karnataka", "timisoara", "cluj-napoca", "bucharest-palazzo",
}


def _slug_to_title(rest: str) -> str:
    """Convert a job slug into a readable title."""
    # strip any trailing ?domain=... query
    rest = rest.split("?")[0]
    rest = unquote(rest)
    words = rest.split("-")
    # drop trailing location tokens to keep only the role title
    while words and words[-1].lower() in _LOCATION_TOKENS:
        words.pop()
    # drop common noise phrases (in order of length) from the remaining slug
    lowered = "-".join(words)
    for phrase in _NOISE_PHRASES:
        lowered = lowered.replace(phrase, "")
    lowered = lowered.replace("--", "-").strip("-")
    words = [w for w in lowered.split("-") if w]
    title = " ".join(w.capitalize() for w in words if w)
    return title.strip() if title else rest.replace("-", " ").title()


def _slug_to_location(rest: str) -> str:
    """Extract a location string from the trailing slug tokens (best effort)."""
    rest = rest.split("?")[0]
    rest = unquote(rest)
    words = rest.split("-")
    loc_words = []
    seen_loc_token = False
    for w in reversed(words):
        if w.lower() in _LOCATION_TOKENS:
            loc_words.append(w)
            seen_loc_token = True
        elif seen_loc_token:
            break
    loc_words.reverse()
    location = ", ".join(w.replace("-", " ").title() for w in loc_words)
    return location


def scrape_microsoft_careers() -> list[ScrapeItem]:
    items: list[ScrapeItem] = []
    logger.info("Fetching Microsoft Careers")

    try:
        resp = httpx.get(MS_SITEMAP, timeout=30, follow_redirects=True,
                         headers={"User-Agent": USER_AGENT})
    except Exception as e:
        logger.error("Microsoft Careers request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Microsoft Careers sitemap returned %d", resp.status_code)
        return items

    locs = re.findall(r"<loc>(.*?)</loc>", resp.text)
    seen = set()
    for loc in locs:
        if "/careers/job/" not in loc:
            continue
        slug = loc.split("/")[-1]
        if "intern" not in slug.lower():
            continue
        m = re.match(r"(\d+)-(.+)", slug)
        if not m:
            continue
        job_id, rest = m.group(1), m.group(2)
        if job_id in seen:
            continue
        seen.add(job_id)

        title = _slug_to_title(rest)
        location = _slug_to_location(rest) or "Various"
        # keep the canonical job URL (strip any query for a clean shareable link)
        clean_url = loc.split("?")[0]

        item = ScrapeItem(
            title=f"[Microsoft] {title}",
            type="Internship",
            source="Microsoft Careers",
            link=clean_url,
            deadline="",
            eligibility="Students and recent graduates; global",
            tags=["microsoft", "internship", "careers", "tech"],
            location=location,
            organizer="Microsoft",
            notes="Source: apply.careers.microsoft.com (public sitemap).",
        )
        if not item.validate():
            items.append(item)

    if not items:
        item = ScrapeItem(
            title="Microsoft Internships", type="Internship", source="Microsoft Careers",
            link=MS_SEARCH, deadline="",
            eligibility="Students and recent graduates; global",
            tags=["microsoft", "internship", "swe", "tech"],
            location="Various", organizer="Microsoft",
            notes="Visit link for current openings. Source: jobs.careers.microsoft.com.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Microsoft Careers: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_microsoft_careers()
    print(f"Microsoft Careers: {len(results)} items")
    for item in results[:20]:
        print(f"  {item.title[:60]} | {item.location[:25]} | {item.link[:60]}")
