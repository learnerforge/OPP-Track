"""
Unstop hackathon and internship scraper — API-based.
Uses the public Unstop API for reliable, structured data extraction.
No authentication required. Returns rich JSON with all fields.
"""

from __future__ import annotations

import re
import json
import logging
import requests
from datetime import datetime
from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, classify_location

logger = logging.getLogger(__name__)

UNSTOP_API = "https://unstop.com/api/public/opportunity/search-result"

ENDPOINTS = [
    {"opportunity": "hackathons", "oppstatus": "open", "label": "Hackathon"},
    {"opportunity": "competitions", "oppstatus": "open", "label": "Competition"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _parse_iso_date(iso_str: str) -> str:
    """Parse ISO datetime string to YYYY-MM-DD."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("+05:30", "+05:30"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return parse_deadline(iso_str)


def _compute_duration(start_iso: str, end_iso: str) -> str:
    """Compute human-readable duration from two ISO dates."""
    if not start_iso or not end_iso:
        return ""
    try:
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        delta = end - start
        days = delta.days
        if days <= 0:
            return ""
        if days == 1:
            return "1 Day"
        if days < 7:
            return f"{days} Days"
        weeks = days // 7
        remaining = days % 7
        if remaining:
            return f"{weeks} Weeks {remaining} Days"
        return f"{weeks} Weeks"
    except (ValueError, TypeError):
        return ""


def _sum_prizes(prizes: list[dict]) -> str:
    """Sum all prize amounts and format as currency string."""
    if not prizes:
        return ""
    total = 0
    currency_symbol = ""
    for prize in prizes:
        if not isinstance(prize, dict):
            continue
        cash = prize.get("cash") or 0
        if isinstance(cash, (int, float)):
            total += int(cash)
        curr = prize.get("currency", "")
        if curr == "fa-rupee" or curr == "INR":
            currency_symbol = "\u20b9"
        elif curr == "USD":
            currency_symbol = "$"
        others = prize.get("others", "")
        if others and not total:
            return str(others)
    if total > 0:
        if not currency_symbol:
            currency_symbol = "\u20b9"
        return f"{currency_symbol}{total:,}"
    return ""


def _extract_eligibility(filters: list[dict], title: str = "") -> str:
    """Extract eligibility from structured filter data."""
    if not filters:
        return "Check Unstop for eligibility details"
    elig_parts = []
    for f in filters:
        if not isinstance(f, dict):
            continue
        ftype = f.get("type", "")
        fname = f.get("name", "")
        if ftype == "eligible" and fname:
            elig_parts.append(fname)
    if not elig_parts:
        return "Check Unstop for eligibility details"
    return ", ".join(elig_parts[:6])


def _extract_tags(item: dict) -> list[str]:
    """Extract tags from workfunction, required_skills, and filters."""
    tags = []
    # Skills
    for skill in item.get("required_skills", []):
        if isinstance(skill, dict):
            name = skill.get("skill") or skill.get("skill_name", "")
            if name:
                tags.append(name)
    # Work functions
    for wf in item.get("workfunction", []):
        if isinstance(wf, dict):
            name = wf.get("name", "")
            if name:
                tags.append(name)
    # Deduplicate and limit
    seen = set()
    result = []
    for t in tags:
        if t.lower() not in seen:
            seen.add(t.lower())
            result.append(t)
    return result[:8]


def _extract_location(item: dict) -> str:
    """Extract location from region and address data."""
    region = item.get("region", "")
    address = item.get("address_with_country_logo", {})
    if isinstance(address, dict):
        parts = []
        for key in ("city", "state", "country"):
            val = address.get(key)
            if val:
                parts.append(str(val))
        if parts:
            return ", ".join(parts)
    if region:
        return region.capitalize()
    return ""


def scrape_unstop() -> list[ScrapeItem]:
    """Scrape hackathons and competitions from Unstop via public API."""
    items: list[ScrapeItem] = []
    seen_titles: set[str] = set()

    for endpoint in ENDPOINTS:
        page_num = 1
        label = endpoint["label"]
        logger.info(f"Fetching Unstop ({label}): page {page_num}")

        while True:
            params = {
                "opportunity": endpoint["opportunity"],
                "page": page_num,
                "per_page": 100,
                "oppstatus": endpoint["oppstatus"],
            }

            try:
                resp = requests.get(UNSTOP_API, params=params, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                data = resp.json().get("data", {})
                page_items = data.get("data", [])
                last_page = data.get("last_page", 1)
            except Exception as e:
                logger.error(f"Unstop API error for {label} page {page_num}: {e}")
                break

            if not page_items:
                break

            for item in page_items:
                title = item.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                link = item.get("public_url", "")
                if link and not link.startswith("http"):
                    link = f"https://unstop.com/{link}"
                short_url = item.get("short_url", "")
                if not link and short_url:
                    link = short_url

                if not link:
                    continue

                # Dates
                regn = item.get("regnRequirements", {}) if isinstance(item.get("regnRequirements"), dict) else {}
                regn_start = regn.get("start_regn_dt", "")
                regn_end = regn.get("end_regn_dt", "")
                end_date = item.get("end_date", "")
                deadline = _parse_iso_date(regn_end or end_date)

                # Duration
                duration = _compute_duration(regn_start, end_date)

                # Organizer
                org = item.get("organisation", {})
                organizer = org.get("name", "") if isinstance(org, dict) else str(org) if org else ""

                # Prize
                prize_pool = _sum_prizes(item.get("prizes", []))

                # Participants
                register_count = item.get("registerCount", 0)
                participants = str(register_count) if register_count else ""

                # Tags
                tags = _extract_tags(item)

                # Eligibility
                eligibility = _extract_eligibility(item.get("filters", []), title)

                # Location
                raw_location = _extract_location(item)
                location = classify_location(raw_location) if raw_location else ""
                detailed_location = raw_location

                # Type
                opp_type = "Hackathon" if "hackathon" in endpoint["opportunity"] else "Competition"

                # Notes
                notes_parts = [f"Source: Unstop."]
                if organizer:
                    notes_parts.append(f"Org: {organizer}.")
                if detailed_location:
                    notes_parts.append(f"Location: {detailed_location}.")
                if participants:
                    notes_parts.append(f"Registered: {participants}.")
                if duration:
                    notes_parts.append(f"Duration: {duration}.")

                item_obj = ScrapeItem(
                    title=title,
                    type=opp_type,
                    source="Unstop",
                    link=link,
                    deadline=deadline,
                    eligibility=eligibility,
                    tags=tags,
                    notes=" ".join(notes_parts),
                    location=location,
                    organizer=organizer,
                    prize_pool=prize_pool,
                    participants=participants,
                    duration=duration,
                )
                items.append(item_obj)
                logger.info(f"  Found: {title} | deadline={deadline} | prize={prize_pool} | participants={participants}")

            if page_num >= last_page:
                break
            page_num += 1
            logger.info(f"Fetching Unstop ({label}): page {page_num}")

    logger.info(f"Unstop: scraped {len(items)} opportunities")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_unstop()
    for item in results:
        print(f"  {item.title} | {item.type} | deadline={item.deadline} | prize={item.prize_pool} | participants={item.participants} | duration={item.duration}")
