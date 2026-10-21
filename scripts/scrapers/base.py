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


_OLD_YEAR_RE = re.compile(r'(?<!\d)20(?:0\d|1\d|2[0-3])(?!\d)')


def filter_stale(items: list[ScrapeItem]) -> list[ScrapeItem]:
    """Drop items that are expired or reference pre-2024 years.

    - Items whose deadline has already passed are dropped.
    - Items with no deadline (rolling/evergreen) are kept.
    - Items whose URL or title contains a standalone 2000-2023 year
      (e.g. dead 2021-2023 challenge pages) are dropped.
    """
    today = date.today()
    kept: list[ScrapeItem] = []
    dropped = 0
    for item in items:
        if item.deadline:
            try:
                deadline_date = datetime.strptime(item.deadline, "%Y-%m-%d").date()
            except ValueError:
                deadline_date = None
            if deadline_date and deadline_date < today:
                dropped += 1
                continue
        if _OLD_YEAR_RE.search(f"{item.link} {item.title}"):
            dropped += 1
            continue
        kept.append(item)
    return kept


class ScrapeBlocked(Exception):
    """Raised when a source refuses to serve us (403/429/Cloudflare/etc).

    This is deliberately distinct from "the source returned no items". A blocked
    source is a *transport* failure: the site is up, we are not allowed to read
    it. Conflating the two (the previous behaviour — every scraper just
    ``return []``) makes a block indistinguishable from a genuinely empty
    listing, so the daily pipeline reported "source regressed -100%" instead of
    "we were blocked", and the real cause was invisible in the logs.

    ``run_all.run_scraper`` catches this separately and records the source as
    ``blocked`` rather than ``error`` or ``empty``.

    Attributes:
        source: human-readable source label, when known.
        status: the HTTP status code that triggered the block, if any.
    """

    def __init__(self, message: str = "", *, source: str = "", status: int | None = None):
        super().__init__(message)
        self.source = source
        self.status = status


# Responses that mean "you may not read this", not "this is empty":
#   403 forbidden, 429 rate-limited, 503 with a challenge body.
_BLOCK_STATUS = frozenset({403, 429, 503})
# Cloudflare / Akamai / generic interstitial markers. Matched case-insensitively
# against the first few KB of the body only.
_INTERSTITIAL_MARKERS = (
    "just a moment",
    "attention required",
    "checking your browser",
    "enable javascript and cookies",
    "cf-browser-verification",
    "access denied",
    "captcha",
    "unusual traffic",
)


def is_blocked_response(resp) -> bool:
    """True when an httpx-like response is a bot block rather than content.

    Shared so scrapers stop re-implementing this: ``angelhack.py`` had its own
    ``_is_cloudflare_block`` whose result was then thrown away and reported as
    an empty list.

    Detect by status code first, then by interstitial markers in the body.
    Only the head of the body is inspected, so a page that merely *mentions*
    a captcha further down is not misclassified.
    """
    status = getattr(resp, "status_code", None)
    if status in _BLOCK_STATUS:
        return True
    try:
        head = (resp.text or "")[:4096].lower()
    except Exception:  # a streaming/errored response has no .text
        return False
    return any(marker in head for marker in _INTERSTITIAL_MARKERS)


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
    """Remove duplicates by link URL, keeping the item with more data.

    Links are compared through ``normalize_link``, so scheme, ``www.``, query
    strings, fragments and trailing slashes do not disguise the same
    opportunity as two separate ones.
    """
    link_map: dict[str, ScrapeItem] = {}
    result: list[ScrapeItem] = []
    for item in items:
        link_key = normalize_link(item.link)
        if not link_key:
            result.append(item)
            continue
        if link_key in link_map:
            existing = link_map[link_key]
            existing_score = sum(1 for v in [existing.deadline, existing.eligibility, existing.location, existing.prize_pool, existing.organizer, existing.participants] if v)
            new_score = sum(1 for v in [item.deadline, item.eligibility, item.location, item.prize_pool, item.organizer, item.participants] if v)
            if new_score > existing_score:
                # Replace existing with richer item
                result = [x for x in result if normalize_link(x.link) != link_key]
                result.append(item)
                link_map[link_key] = item
        else:
            link_map[link_key] = item
            result.append(item)
    return result


# Query parameters that never identify a resource — tracking/campaign cruft.
# Everything else in a query string is preserved: for sites like SIGNATE every
# competition shares one path and is distinguished only by `?competition=<id>`.
_TRACKING_PARAM_RE = re.compile(
    r'^(utm_[a-z_]+|ref[a-z_]*|referrer|source|fbclid|gclid|mc_cid|mc_eid|igshid|si)$',
    re.I,
)


def normalize_link(url: str) -> str:
    """Reduce a URL to a canonical form for cross-source comparison.

    Strips the scheme, a leading ``www.``, any *tracking* query parameters, and
    a trailing slash, then lowercases. Tracking parameters (``?ref_feature=...``
    on Devpost, ``?utm_source=...`` elsewhere) otherwise make the same
    opportunity look like two different links.

    Meaningful parts of the URL are kept, because several sources encode the
    identity there: ``?competition=<id>`` distinguishes SIGNATE competitions
    that share one path, and ``#funding`` / ``#eligibility`` distinguish the
    sections of a single Mitacs page that are each listed as its own item.
    """
    if not url:
        return ""
    key = url.strip().lower()
    key = re.sub(r'^https?://', '', key)
    key = re.sub(r'^www\.', '', key)

    if '?' in key:
        path, _, query = key.partition('?')
        kept = [
            part for part in query.split('&')
            if part and not _TRACKING_PARAM_RE.match(part.split('=', 1)[0])
        ]
        key = f"{path}?{'&'.join(kept)}" if kept else path

    return key.rstrip('/')


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
