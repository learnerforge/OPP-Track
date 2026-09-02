"""
Base scraper infrastructure — output schema and utilities.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional


@dataclass
class ScrapeItem:
    """Normalized scraped opportunity — matches the Opportunity TypeScript type."""

    title: str
    type: str  # 'Hackathon' | 'Internship' | 'Certification'
    source: str
    link: str
    deadline: str  # YYYY-MM-DD
    eligibility: str
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    date_added: str = field(default_factory=lambda: date.today().isoformat())
    location: str = ""  # Online / Hybrid / Offline
    prize_pool: str = ""
    participants: str = ""
    organizer: str = ""
    duration: str = ""

    @property
    def fingerprint(self) -> str:
        """Deterministic hash for deduplication across runs."""
        raw = f"{self.title.lower().strip()}|{self.source.lower().strip()}|{self.type.lower().strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        return d

    def validate(self) -> list[str]:
        """Return list of validation errors (empty = valid)."""
        errors = []
        if not self.title.strip():
            errors.append("title is empty")
        if self.type not in ("Hackathon", "Internship", "Certification", "Competition"):
            errors.append(f"invalid type: {self.type}")
        if not self.source.strip():
            errors.append("source is empty")
        if self.deadline:
            try:
                datetime.strptime(self.deadline, "%Y-%m-%d")
            except ValueError:
                errors.append(f"invalid deadline format: {self.deadline} (expected YYYY-MM-DD)")
        if self.link and not self.link.startswith(("http://", "https://")):
            errors.append(f"invalid link: {self.link}")
        return errors


def parse_deadline(raw: str) -> str:
    """Try to parse a deadline string into YYYY-MM-DD format.

    Handles common formats found on hackathon/internship sites:
    - "2026-08-15"
    - "Aug 15, 2026"
    - "15 Aug 2026"
    - "2026/08/15"
    - "15-08-2026"
    - "Ended" / "Past" / empty → returns empty string
    """
    if not raw or raw.lower() in ("ended", "past", "expired", "closed", "n/a", "tba", "tbh"):
        return ""

    raw = raw.strip()

    # Normalize abbreviated month names that differ from the standard 3-letter
    # ``%b`` tokens so that strptime can parse them (e.g. "Sept" -> "Sep").
    _MONTH_ALIASES = {
        "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "may": "May",
        "jun": "Jun", "jul": "Jul", "aug": "Aug", "sept": "Sep", "sep": "Sep",
        "oct": "Oct", "nov": "Nov", "dec": "Dec",
    }
    def _map_month(match: "re.Match") -> str:
        word = match.group(1)
        return _MONTH_ALIASES.get(word.lower(), word)
    raw = re.sub(r'\b([A-Za-z]+)\.?', _map_month, raw)

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try month-day patterns without year (assume current year)
    year = datetime.now().year
    month_day_formats = [
        "%b %d",
        "%B %d",
        "%d %b",
        "%d %B",
    ]
    for fmt in month_day_formats:
        try:
            dt = datetime.strptime(raw, fmt).replace(year=year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try to extract a date pattern from free text
    match = re.search(r'(\w+ \d{1,2},?\s*\d{4})', raw)
    if match and match.group(1) != raw:
        return parse_deadline(match.group(1))

    return ""


def clean_text(text) -> str:
    """Collapse whitespace and strip. Handles Selector/TextHandler objects."""
    if text is None:
        return ""
    text_str = str(text)
    if not text_str:
        return ""
    return re.sub(r'\s+', ' ', text_str).strip()


def deduplicate(items: list[ScrapeItem]) -> list[ScrapeItem]:
    """Remove duplicates by fingerprint, keeping first occurrence."""
    seen: set[str] = set()
    result = []
    for item in items:
        fp = item.fingerprint
        if fp not in seen:
            seen.add(fp)
            result.append(item)
    return result


def deduplicate_by_link(items: list[ScrapeItem]) -> list[ScrapeItem]:
    """Remove duplicates by link URL, keeping the item with more data."""
    link_map: dict[str, ScrapeItem] = {}
    result: list[ScrapeItem] = []
    for item in items:
        link_key = item.link.rstrip("/").lower()
        if not link_key:
            result.append(item)
            continue
        if link_key in link_map:
            existing = link_map[link_key]
            existing_score = sum(1 for v in [existing.deadline, existing.eligibility, existing.location, existing.prize_pool, existing.organizer, existing.participants] if v)
            new_score = sum(1 for v in [item.deadline, item.eligibility, item.location, item.prize_pool, item.organizer, item.participants] if v)
            if new_score > existing_score:
                # Replace existing with richer item
                result = [x for x in result if x.link.rstrip("/").lower() != link_key]
                result.append(item)
                link_map[link_key] = item
        else:
            link_map[link_key] = item
            result.append(item)
    return result


_OFFLINE_KEYWORDS = re.compile(
    r'\b(in[- ]?person|on[- ]?site|campus|onsite|physical|venue)\b', re.I
)
_ONLINE_KEYWORDS = re.compile(
    r'\b(virtual|remote|online|digital|anywhere|worldwide)\b', re.I
)


def classify_location(text: str) -> str:
    """Map free-text to one of Online / Hybrid / Offline."""
    if not text:
        return "Online"
    text_lower = text.lower()
    has_online = bool(_ONLINE_KEYWORDS.search(text_lower))
    has_offline = bool(_OFFLINE_KEYWORDS.search(text_lower))
    if has_online and has_offline:
        return "Hybrid"
    if has_offline:
        return "Offline"
    return "Online"


def quality_score(item: ScrapeItem) -> int:
    """Rate completeness of a ScrapeItem on a 0–100 scale.

    Scoring breakdown (100 points total):
      title        20
      type         10
      link         15
      deadline     15
      eligibility  10
      tags          5
      location     10
      prize_pool    5
      participants  5
      organizer     5
    """
    score = 0
    if item.title.strip():
        score += 20
    if item.type.strip():
        score += 10
    if item.link.strip():
        score += 15
    if item.deadline.strip():
        score += 15
    if item.eligibility.strip():
        score += 10
    if item.tags:
        score += 5
    if item.location.strip():
        score += 10
    if item.prize_pool.strip():
        score += 5
    if item.participants.strip():
        score += 5
    if item.organizer.strip():
        score += 5
    return score
