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
        if self.type not in ("Hackathon", "Internship", "Certification"):
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
    if match:
        return parse_deadline(match.group(1))

    return ""


def clean_text(text: str) -> str:
    """Collapse whitespace and strip."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


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
